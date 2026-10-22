"""Plain-text citation cleanup and deterministic qualification consistency."""
import re


def grounded_interview(report, history):
    """Keep explicit proposals from being credited as demonstrated experience."""
    proposals=[]
    for turn in history:
        if turn['role']!='user':
            continue
        answer=turn['content']
        if re.search(r'\b(?:would|could|propos\w*|hypothetical|not (?:recorded|performed|past|actual))\b',answer,re.I):
            proposals.append(answer)
    if not proposals:
        return report
    words=set(re.findall(r'\b[a-z]{5,}\b',' '.join(proposals).lower()))-{'about','would','could','which','their','there','these','those','rather','experience','recorded','proposed','actually','details'}
    def qualify(value):
        sentences=re.split(r'(?<=[.!?])\s+',value)
        result=[]
        for sentence in sentences:
            overlap=words.intersection(re.findall(r'\b[a-z]{5,}\b',sentence.lower()))
            if overlap and re.search(r'experience|demonstrat|implemented|\bused\b|applied|collected|\bpast\b',sentence,re.I) and not re.search(r'propos|would|hypothetical|not established|not demonstrated',sentence,re.I):
                result.append('A proposed approach was discussed; its use in a past project is not established by the answer.')
            else:
                result.append(sentence)
        return ' '.join(dict.fromkeys(result))
    for key in ('summary','score_explanation'):
        report[key]=qualify(report[key])
    for key in ('strengths','improvements','next_steps'):
        report[key]=list(dict.fromkeys(qualify(value) for value in report[key]))
    evidence=[]
    for answer in proposals[:3]:
        span=next((part.strip() for part in re.split(r'(?<=[.!?])\s+|\n',answer) if re.search(r'\bwould\b|\bpropos\w*\b|\bhypothetical\b',part,re.I)),answer)
        evidence.append({'status':'proposed_or_mixed; past execution not established','source_quote':span})
        quote=span if len(span)<=400 else span[:397].rsplit(' ',1)[0]+'…'
        report['strengths'].append('Proposed method (not credited as past experience): "'+quote+'"')
    report['proposal_evidence']=evidence
    return report


def plain_prose(value):
    value = re.sub(r'!?\[([^\]\n]+)\]\(\s*https?://[^\s)]+\s*\)', r'\1', value)
    value = re.sub(r'!?\[([^\]\n]+)\]\[[^\]\n]*\]', r'\1', value)
    value = re.sub(r'\[[^\]\n]+\]:\s*https?://\S+', '', value)
    value = re.sub(r'\uE200[^\uE201]*\uE201|\uE202[^\uE201]*\uE201|\[\d+\]|\[citation[^\]]*\]', '', value, flags=re.I)
    return re.sub(r'[ \t]{2,}', ' ', value).strip()


def clean_generated(value):
    if isinstance(value, dict):
        return {key: item if key in ('url', 'source_url', 'source_quote', 'evidence', 'quote', '_sources') else clean_generated(item) for key, item in value.items()}
    if isinstance(value, list):
        return [clean_generated(item) for item in value]
    return plain_prose(value) if isinstance(value, str) else value


def english_evidence(cv, requirement='English'):
    if not re.search(r'\benglish\b', requirement, re.I):
        return ''
    if re.search(r'\bnative\b', requirement, re.I):
        level = r'native|mother tongue'
    elif re.search(r'\bC2\b', requirement, re.I):
        level = r'C2|native|mother tongue'
    else:
        level = r'C1|C2|fluent|native|mother tongue|bilingual'
    for line in cv.splitlines():
        match = re.search(r'\benglish\b([^,;|\n]{0,60})', line, re.I)
        following = re.split(r'\b(?:german|french|spanish|arabic|italian|portuguese)\b', match[1], flags=re.I)[0] if match else ''
        if (match and re.search(r'\b(?:' + level + r')\b', following, re.I)) or re.search(r'\b(?:' + level + r')\b\s+english\b', line, re.I):
            if not re.search(r'\b(?:not|learning|studying|target|aiming|pursuing)\b|in progress', line, re.I):
                return line.strip()
    return ''


def coherent_fit(result, cv):
    matched = list(result['matched_skills'])
    missing = []
    corrected = False
    backend = next((line.strip() for line in cv.splitlines() if re.search(r'\bk6\b',line,re.I) and re.search(r'backend|back.end',line,re.I) and re.search(r'load|performance|benchmark',line,re.I) and not re.search(r'no experience|not used|would|planning',line,re.I)), '')
    # K6 load evidence cannot, by itself, satisfy functional API requirements.
    narrowed=[]
    for item in matched:
        evidence=item['evidence']
        broad=re.search(r'backend|back.end|\bapi\b',item['skill'],re.I)
        load_only=re.search(r'\bk6\b',evidence,re.I) and (backend or re.search(r'load|performance|benchmark',evidence,re.I)) and not re.search(r'functional\s+api|api\s+functional|rest.?assured|(?:contract|component|integration)\s+test',evidence,re.I)
        functional=re.search(r'functional|contract|component|integration',item['skill'],re.I)
        if broad and load_only and (functional or not re.search(r'load|performance',item['skill'],re.I)):
            narrowed.append({**item,'skill':'Backend performance testing (partial coverage)' if backend else 'Load/performance testing (partial coverage)'})
            if not any(entry['skill'].casefold()==item['skill'].casefold() for entry in result['missing_skills']):
                result['missing_skills'].append({'skill':item['skill'],'reason':'Load/performance testing is partial evidence only; functional API coverage needs separate evidence.','priority':'medium'})
            corrected=True
        else:
            narrowed.append(item)
    matched=narrowed
    for item in result['missing_skills']:
        if backend and re.search(r'backend|back.end|\bapi\b',item['skill'],re.I):
            item={**item,'reason':'Partial coverage: backend load/performance automation is evidenced through K6. Functional API, component, integration and contract testing are separate capabilities; this requirement is not fully established by that evidence.', 'partial_evidence':backend}
            if not any(entry['skill']=='Backend performance testing (partial coverage)' for entry in matched):
                matched.append({'skill':'Backend performance testing (partial coverage)','evidence':backend})
            corrected=True
        evidence = english_evidence(cv, item['skill'])
        if evidence:
            if not any(re.search(r'\benglish\b', entry['skill'], re.I) for entry in matched):
                matched.append({'skill': 'English proficiency', 'evidence': evidence})
            corrected = True
            continue
        # Exact labels can be compared safely; Java is never a synonym for JavaScript.
        label = re.sub(r'[^\w]+', ' ', item['skill'].casefold()).strip()
        if any(re.sub(r'[^\w]+', ' ', entry['skill'].casefold()).strip() == label for entry in matched):
            corrected = True
            continue
        missing.append(item)
    result['matched_skills'] = list({(entry['skill'],entry['evidence']):entry for entry in matched}.values())
    result['missing_skills'] = missing
    result['validated_gaps'] = missing
    result['improvements'] = [item for item in result['improvements'] if not english_evidence(cv, item)]
    if backend:
        result['improvements']=['Build on the evidenced K6 backend performance testing; supply separate evidence or practice for the functional API, component, integration or contract coverage required by this offer.' if re.search(r'backend|\bapi\b',item,re.I) and re.search(r'no (?:explicit )?evidence|no experience|lack',item,re.I) else item for item in result['improvements']]
    if corrected:
        result['summary'] = 'CV evidence is shown under matched skills; remaining gaps distinguish partial coverage from capabilities not evidenced in the supplied text. Existing English evidence is excluded from gaps. The model score was not recalculated after resolving category conflicts and is not a hiring probability.'
        result['score_consistency'] = 'Category conflicts were resolved; the model score was not recalculated.'
    return result
