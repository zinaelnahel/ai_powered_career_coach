"""Career Lab routes. Inputs and results remain request-local; no database required."""
from datetime import datetime, timezone
import math
import re
import time
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from flask import jsonify
from job_links import check_job_links, application_key
from content_quality import clean_generated, coherent_fit
from learning_scope import mobile_resources, scope_mobile_week, scope_small_week, rehearsal_questions


SKILLS = ('python', 'javascript', 'typescript', 'react', 'sql', 'excel', 'figma', 'docker',
          'aws', 'java', 'c++', 'git', 'accessibility', 'communication', 'leadership',
          'project management', 'data analysis', 'customer service', 'sales', 'marketing',
          'research', 'testing', 'machine learning', 'power bi', 'tableau', 'agile', 'css', 'html')


# PSEUDOCODE: OUTPUT VALIDATION HELPERS
# CHECK AI objects, text, lists, numeric ranges and allowed URLs.
# RAISE a readable error when a required value is missing or invalid.
def obj(value):
    if not isinstance(value, dict):
        raise ValueError('The AI returned an invalid result. Please retry.')
    return value


def text(value, key, limit=6000, minimum=1):
    data = obj(value)
    item = data.get(key)
    if not isinstance(item, str) or not minimum <= len(item.strip()) <= limit:
        raise ValueError('The AI returned an incomplete result. Please retry.')
    return item.strip()


def array(value, key, maximum=24):
    items = obj(value).get(key)
    if not isinstance(items, list) or len(items) > maximum:
        raise ValueError('The AI returned an invalid list. Please retry.')
    return items


def strings(value, key, minimum=1):
    items = array(value, key)
    if len(items) < minimum or not all(isinstance(x, str) and 0 < len(x.strip()) <= 6000 for x in items):
        raise ValueError('The AI returned incomplete advice. Please retry.')
    return items


def number(value, low, high):
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError('The AI returned an invalid score or time budget. Please retry.')
    return value


def url(value):
    if not isinstance(value, str) or len(value) > 2048:
        return ''
    try:
        parts = urlsplit(value)
        if parts.scheme != 'https' or not parts.hostname or parts.username or parts.password:
            return ''
        return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ''))
    except ValueError:
        return ''


def source_key(value):
    """Ignore only marketing tags, never job IDs or other functional parameters."""
    link = url(value)
    if not link:
        return ''
    parts = urlsplit(link)
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True)
             if not key.lower().startswith('utm_')]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ''))


def job_detail_url(value):
    parts = urlsplit(value)
    path = parts.path.lower().rstrip('/')
    query = dict(parse_qsl(parts.query))
    host = (parts.hostname or '').lower()
    if re.search(r'(^|\.)indeed\.[a-z.]+$', host):
        return bool(path in ('/viewjob', '/rc/clk') and query.get('jk'))
    if path in ('/search', '/job-search', '/jobs/search', '/vacancies', '/empleos'):
        return False
    return bool(path and path not in ('/jobs', '/careers', '/career', '/positions', '/openings')
                and not any(marker in path for marker in ('/locations/', '/jobs/search', '/search-jobs', '-jobs-in-', '/qa-testing')))


# PSEUDOCODE: SOURCE PROVENANCE
# READ source metadata supplied by the provider web-search tool.
# KEEP usable HTTPS sources and require at least one.
# LATER accept citations only if their URLs appear in this collection.
def sources(result):
    found = {}
    for source in result.get('_sources', []):
        if isinstance(source, dict) and (link := url(source.get('url'))):
            title = source.get('title')
            found[link] = {'url': link, 'title': title[:250] if isinstance(title, str) and title else urlsplit(link).hostname}
    if not found:
        raise ValueError('Web research returned no usable sources. Please retry; no unverified results were substituted.')
    return found


def keyword_skills(value):
    return [skill for skill in SKILLS if re.search(r'(?<!\w)' + re.escape(skill) + r'(?!\w)', value, re.I)]


def learning_resources(week):
    """Curated official URLs, never model-generated links."""
    topic = ' '.join([week['focus'], week['resource_hint'], week.get('deliverable', ''), *[item.get('task', '') for item in week.get('activities', [])]])
    # Objective wins over an incidental language or stale generated publisher.
    for pattern,title,link in [
        (r'distributed|resilien|fault.toleran|timeout|retr(?:y|ies)', 'Google SRE: Testing for Reliability', 'https://sre.google/sre-book/testing-reliability/'),
        (r'mock|stub|virtuali[sz]', 'WireMock: stubbing', 'https://wiremock.org/docs/stubbing/'),
        (r'\bapi\b|rest.?assured|\bhttp\b', 'REST Assured: usage guide', 'https://github.com/rest-assured/rest-assured/wiki/Usage')]:
        if re.search(pattern,week['focus'],re.I):
            return [{'title':title,'url':link}]
    if re.search(r'ci/cd|continuous (?:integration|delivery|deployment)|pipeline|github actions|gitlab ci', week['focus'], re.I):
        if re.search(r'gitlab', topic, re.I):
            return [{'title': 'GitLab: create and run your first CI/CD pipeline', 'url': 'https://docs.gitlab.com/ci/quick_start/'}]
        if re.search(r'github', topic, re.I):
            return [{'title': 'GitHub: understanding Actions', 'url': 'https://docs.github.com/en/actions/get-started/understand-github-actions'}]
        # An explicit platform choice avoids labeling GitHub documentation as GitLab advice.
        return [{'title': 'CI/CD practice option: GitHub Actions workflows', 'url': 'https://docs.github.com/en/actions/get-started/understand-github-actions'}]
    # Match the learning objective before incidental UI/testing tool names.
    if re.search(r'\bllm\b|language model', topic, re.I) and re.search(r'robust|adversarial|prompt injection|red.?team|garak', topic, re.I):
        return [{'title': 'garak: your first LLM vulnerability scan', 'url': 'https://docs.garak.ai/garak/llm-scanning-basics/your-first-scan'}]
    if re.search(r'\bllm\b|language model', topic, re.I) and re.search(r'dataset|test.?set|baseline|custom task|benchmark', topic, re.I):
        return [{'title': 'Hugging Face Lighteval: adding a custom evaluation task', 'url': 'https://huggingface.co/docs/lighteval/en/adding-a-custom-task'}]
    mobile = mobile_resources(week['focus'] + ' ' + week['resource_hint'])
    if mobile:
        return mobile
    # Prefer the named publisher/chapter over incidental broad skill keywords.
    specific = [
        (r'\bmockito\b', 'Mockito 5.24.0: stubbing and behavior verification', 'https://javadoc.io/static/org.mockito/mockito-core/5.24.0/org/mockito/Mockito.html'),
        (r'\bwiremock\b|service virtualization', 'WireMock: stubbing HTTP responses', 'https://wiremock.org/docs/stubbing/'),
        (r'rest.?assured|backend.*api|api.*(?:test|validat)', 'REST Assured: usage guide', 'https://github.com/rest-assured/rest-assured/wiki/Usage'),
        (r'\bkotlin\b', 'Kotlin: basic syntax', 'https://kotlinlang.org/docs/basic-syntax.html'),
        (r'distributed systems|fault injection|failure scenario|resilien', 'Google SRE, chapter 17: Testing for Reliability', 'https://sre.google/sre-book/testing-reliability/'),
        (r'\bjava\b|object.oriented', 'Java: classes and objects', 'https://dev.java/learn/classes-objects/'),
        (r'gitlab', 'GitLab: create and run your first CI/CD pipeline', 'https://docs.gitlab.com/ci/quick_start/'),
        (r'lighteval', 'Hugging Face Lighteval: Quick Tour', 'https://huggingface.co/docs/lighteval/en/quicktour'),
        (r'custom metric|creating.*evaluation|new metric', 'Hugging Face Evaluate: creating and sharing a new evaluation', 'https://huggingface.co/docs/evaluate/en/creating_and_sharing'),
        (r'choos.*metric|metric selection|precision|recall|\bf1\b', 'Hugging Face Evaluate: choosing a metric', 'https://huggingface.co/docs/evaluate/en/choosing_a_metric'),
        (r'evaluation.?suite|evaluation suite', 'Hugging Face Evaluate: creating an EvaluationSuite', 'https://huggingface.co/docs/evaluate/en/evaluation_suite'),
        (r'bias|fairness|limitation|considerations', 'Hugging Face Evaluate: considerations for model evaluation', 'https://huggingface.co/docs/evaluate/en/considerations'),
        (r'pytest.*fixture|fixture', 'pytest: how to use fixtures', 'https://docs.pytest.org/en/stable/how-to/fixtures.html'),
    ]
    for candidate in (week['resource_hint'], week['focus']):
        for pattern, title, link in specific:
            if re.search(pattern, candidate, re.I):
                return [{'title': title, 'url': link}]
    catalog = [
        (r'\bllm\b|model evaluation|hugging face|lighteval', 'Hugging Face: model evaluation overview', 'https://huggingface.co/docs/evaluate/index'),
        (r'\bplaywright\b', 'Playwright documentation', 'https://playwright.dev/docs/intro'),
        (r'\bk6\b', 'Grafana k6: using k6', 'https://grafana.com/docs/k6/latest/using-k6/'),
        (r'\bpytest\b', 'pytest documentation', 'https://docs.pytest.org/en/stable/'),
        (r'github actions', 'GitHub: understanding Actions', 'https://docs.github.com/en/actions/get-started/understand-github-actions'),
        (r'\bpython\b', 'Python tutorial', 'https://docs.python.org/3/tutorial/'),
    ]
    for candidate in (week['resource_hint'], week['focus']):
        matches = [{'title': title, 'url': link} for pattern, title, link in catalog if re.search(pattern, candidate, re.I)]
        if matches:
            return matches[:2]
    return []


# PSEUDOCODE: DEMO JOB FIT
# FIND supported skill keywords in the offer and CV.
# SPLIT required skills into evidenced and missing keywords.
# RETURN overlap percentage, actual CV excerpts and illustrative advice.
def demo_fit(cv, description):
    required = keyword_skills(description)
    present = keyword_skills(cv)
    matched = [skill for skill in required if skill in present]
    missing = [skill for skill in required if skill not in present]
    evidence = []
    for skill in matched:
        match = re.search(re.escape(skill), cv, re.I)
        evidence.append({'skill': skill, 'evidence': cv[max(0, match.start() - 30):match.end() + 75]})
    return {'score': round(100 * len(matched) / len(required)) if required else 0,
            'summary': 'Demo keyword overlap only, not a semantic assessment or hiring prediction. Missing means not evidenced in this CV text.' if required else 'No supported demo skill keywords were found in this job description. Use live AI for semantic analysis; the demo score is not meaningful here.',
            'matched_skills': evidence,
            'missing_skills': [{'skill': skill, 'reason': 'Mentioned in the job description but not found in the CV text.', 'priority': 'high'} for skill in missing],
            'improvements': ['Add a specific, truthful example for each relevant requirement you can demonstrate.', 'If you lack evidence for a requirement, build a small project or practice task before claiming proficiency.']}


# PSEUDOCODE: CV EVIDENCE MATCHING
# NORMALIZE safe typography and whitespace while mapping back to original positions.
# SEARCH for a continuous matching quotation, allowing outer quote wrappers.
# IF found, return the original CV excerpt.
# OTHERWISE reject the claim; do not accept semantic guesses or changed numbers.
def cv_evidence_excerpt(cv, quote):
    """Match typography/spacing differences and return the original CV excerpt.

    Do not use fuzzy or semantic matching: changed words or metrics must fail.
    """
    typography = str.maketrans({
        '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"',
        '\u2010': '-', '\u2011': '-', '\ufb01': 'fi', '\ufb02': 'fl',
    })

    def normalize(value):
        output, positions = [], []
        for index, character in enumerate(value):
            if character == '\u00ad':
                continue
            for part in character.translate(typography).casefold():
                if part.isspace():
                    part = ' '
                    if output and output[-1] == ' ':
                        continue
                output.append(part)
                positions.append(index)
        return ''.join(output), positions

    source, positions = normalize(cv)
    needle = normalize(quote)[0].strip()
    candidates = [needle]
    if len(needle) > 2 and needle[0] == needle[-1] and needle[0] in ('"', "'"):
        candidates.append(needle[1:-1].strip())
    for candidate in candidates:
        if candidate and (start := source.find(candidate)) >= 0:
            return cv[positions[start]:positions[start + len(candidate) - 1] + 1]
    raise ValueError('The AI cited evidence that could not be verified in your CV. Your CV is still here; please try the fit check again.')


def register_career_features(app, generate, body, field):
    def research(instructions, context, **kwargs):
        # Retry malformed search output once, never credentials, quota or outages.
        started = time.monotonic()
        for attempt in range(2):
            try:
                return clean_generated(generate(instructions + ' Return plain text inside JSON string fields: no inline Markdown links or citation tokens; URLs belong only in structured source fields.' + (' Return exactly one complete JSON object without prose, markdown or citation markers in field values.' if attempt else ''), context, **kwargs))
            except ValueError as error:
                # Each web attempt is capped at 35 seconds, leaving room for
                # one repair attempt and source verification within the 90-second budget.
                if attempt or time.monotonic() - started > 35 or not any(message in str(error) for message in ('invalid response', 'response was incomplete')):
                    raise

    # PSEUDOCODE: FIND JOBS
    # VALIDATE role/location; return a fictional listing in demo mode.
    # OTHERWISE require web research and collect retrieved sources.
    # KEEP only listings whose safe URLs occur in those sources.
    # RETURN listings, source links and the research timestamp.
    @app.post('/api/jobs')
    def jobs():
        data = body()
        role = field(data, 'role', 160, 2)
        location = field(data, 'location', 160)
        if data.get('demo') is True:
            offers = [{'title': role, 'company': 'Example Studio (fictional)', 'location': location or 'Remote',
                       'description': f'Sample {role} opening. Work collaboratively, communicate clearly, and demonstrate relevant skills. This is a fictional listing for exploring the workflow.', 'url': None, 'posted_at': None}]
            return jsonify(jobs=offers, sources=[], demo=True, searched_at=None,
                           summary='Sample listing only. Turn off demo mode to search for real opportunities.')
        result = research('Search several distinct queries and collect up to 16 currently advertised jobs matching role and location, from multiple employers. Use separate searches for the requested title, equivalent automation/testing titles, and direct ATS postings; do not stop after finding the first suitable employer. Keep descriptions concise (at most 50 words) to leave room for candidate coverage. Search role synonyms and direct employer/ATS postings, including Greenhouse and Lever. A Senior QA Engineer query also covers Senior QA Automation Engineer. For country searches, include local cities and city-country headers (for example Valencia, Spain); for city searches include its country. A job header need not contain the literal word Location. Never require the exact input title; equivalent senior QA automation roles qualify; for a location expressed as alternatives (Spain or remote EU), search each alternative separately and combine relevant results. Do not require both alternatives simultaneously. Prefer direct employer job pages over aggregators. Return JSON only: {"summary":"brief search limitations", "jobs":[{"title":"...","company":"...","location":"...","description":"requirements and responsibilities from source, no invented details","url":"exact sourced job URL","posted_at":null,"location_evidence":{"quote":"exact contiguous source text establishing the workplace or permitted remote work country, not an office footer or citizenship requirement","place":"one explicitly permitted workplace country, region or city in that quote","mode":"onsite|hybrid|remote"}}]}. Return an empty jobs list if no specific offers are found. Never invent an employer, job URL, opening, date, or salary. Use null if a posting date is unavailable. A job must link to a specific opening, not a generic careers page. Include only roles whose main responsibilities match the requested role and whose advertised location or remote eligibility fits the requested location. Do not substitute adjacent SRE, DevOps or security jobs for QA/testing roles. If remote eligibility cannot be established, omit the listing. For Spain, Hybrid Athens is ineligible. Remote alone is insufficient: require explicit permission to work from Spain or a region explicitly including Spain. Do not infer eligibility from company offices, EU citizenship, timezone or willingness to relocate. Prefer fewer relevant offers to unrelated alternatives.',
                          {'role': role, 'location': location, 'date': datetime.now(timezone.utc).date().isoformat()}, web=True)
        refs = sources(result)
        indexed_refs = {source_key(link): source for link, source in refs.items()}
        offers = []
        candidates = obj(result).get('jobs')
        if not isinstance(candidates, list):
            raise ValueError('The AI returned an invalid list. Please retry.')
        candidates = candidates[:16]
        for item in candidates:
            link = url(obj(item).get('url'))
            if source_key(link) not in indexed_refs or not job_detail_url(link) or any(source_key(offer['url']) == source_key(link) for offer in offers):
                continue
            offers.append({key: text(item, key, 6000 if key == 'description' else 250) for key in ('title', 'company', 'location', 'description')} | {'url': link, '_requested_location': location, 'location_evidence': item.get('location_evidence'), 'posted_at': item.get('posted_at') if isinstance(item.get('posted_at'), str) else None})
        # Search tools may retrieve a relevant ATS page that the generated shortlist
        # omits. Recover its fields from the actual page, never from a guessed URL.
        discovered = 0
        if re.search(r'\bqa\b|quality assurance|test.*engineer', role, re.I):
            for link in refs:
                parts = urlsplit(link)
                if parts.hostname not in ('job-boards.greenhouse.io', 'boards.greenhouse.io') or not re.fullmatch(r'/[^/]+/jobs/\d+/?', parts.path):
                    continue
                if any(source_key(offer['url']) == source_key(link) for offer in offers):
                    continue
                offers.append({'title': role, 'company': parts.path.split('/')[1], 'location': '',
                               'description': '', 'url': link, 'posted_at': None,
                               '_requested_location': location, '_discover_role': role})
                discovered += 1
                if discovered == 16:
                    break
        # PSEUDOCODE: POST-FILTER SEARCH MESSAGING
        # BUILD the summary from accepted cards, not the model's unfiltered claims.
        # SHOW citations only for the listings actually displayed.
        accepted_sources = len(offers)
        offers = check_job_links(offers)
        checks = getattr(offers, 'checks', {})
        if location:
            offers = [offer for offer in offers if offer.get('location_verified') is True]
        for offer in offers:
            offer.pop('_requested_location', None)
            offer.pop('_discover_role', None)
            if not offer.get('location_verified'):
                offer.pop('location_evidence', None)
        unique = {}
        for offer in offers:
            identity = application_key(offer.get('application_url') or offer['url'])
            current = unique.get(identity)
            if current is None or application_key(offer['url']) == identity:
                unique[identity] = offer
        duplicate_count = len(offers) - len(unique)
        offers = list(unique.values())
        count = len(offers)
        diagnostics = {'researched': len(candidates) + discovered, 'source_discovered': discovered, 'source_accepted': accepted_sources, 'shown': count,
                       'source_rejected': len(candidates) + discovered - accepted_sources, 'duplicates_removed': duplicate_count, 'checks': checks}
        summary = (f'{count} source-backed job listing{"s" if count != 1 else ""} returned for {role}. Check the source for current availability and location eligibility.'
                   if count else 'No source-backed job listings could be confirmed for this search. Try a more specific role, one location, or remote eligibility terms. No unverified alternatives were substituted.')
        displayed_sources = list({item['url']: {**indexed_refs[source_key(item['url'])], 'url': item['url']} for item in offers}.values())
        return jsonify(jobs=offers, sources=displayed_sources, demo=False,
                       searched_at=datetime.now(timezone.utc).isoformat(), summary=summary,
                       search_diagnostics=diagnostics, location_policy='Only listings with source-checked workplace geography are shown. Remote alone is insufficient; personal work authorization is not assessed.' if location else None)

    # PSEUDOCODE: LIVE JOB FIT
    # VALIDATE CV, role and offer; select demo or live generation.
    # ASK the model to assess skills, experience and impact with stated weights.
    # VALIDATE score, skill priorities, advice and each CV evidence excerpt.
    # RETURN the verified result structure; weights are instructions to the model.
    @app.post('/api/fit')
    def fit():
        data = body()
        role = field(data, 'role', 160, 2)
        cv = field(data, 'cv', 30000, 80)
        description = field(data, 'description', 12000, 20)
        demo = data.get('demo') is True
        result = demo_fit(cv, description) if demo else generate(
            'Compare CV evidence with the supplied job offer for the role. Return JSON {"score":0-100,"summary":"rationale and limitations","matched_skills":[{"skill":"...","evidence":"exact short CV quote"}],"missing_skills":[{"skill":"...","reason":"job requirement not evidenced in CV","priority":"high|medium|low"}],"improvements":["concrete truthful CV edits or practice actions"]}. Assess required skills (60%), relevant experience (25%), and evidence of impact (15%); explain the weighting in summary. Distinguish not evidenced from not possessed. Requirement categories are mutually exclusive: English C1/C2 is evidence for fluent English, and JavaScript must never be treated as Java. Missing skills must come from the job description, not assumed requirements. Never infer protected attributes or claim a hiring probability. Each evidence value must copy one continuous excerpt from the CV exactly, preserving words, numbers and punctuation. Do not paraphrase, add quotation marks or combine separate excerpts. Omit skills without a supporting excerpt. Empty skill lists are valid.',
            {'role': role, 'cv': cv, 'job_description': description})
        number(result.get('score'), 0, 100)
        text(result, 'summary')
        for item in array(result, 'matched_skills', 40):
            text(item, 'skill', 160)
            quote = text(item, 'evidence', 1000)
            item['evidence'] = cv_evidence_excerpt(cv, quote)
        for item in array(result, 'missing_skills', 40):
            text(item, 'skill', 160)
            text(item, 'reason')
            if item.get('priority') not in ('high', 'medium', 'low'):
                raise ValueError('The AI returned an invalid skill priority. Please retry.')
        strings(result, 'improvements')
        result = coherent_fit(result, cv)
        return jsonify(analysis=result, demo=demo)

    # PSEUDOCODE: LEARNING PLAN
    # REQUIRE a CV, gaps or feedback and validate week/hour settings.
    # BUILD a demo schedule or request a personalized live plan.
    # REQUIRE exactly the requested sequential weeks.
    # CHECK every activity has positive hours and each week fits its budget.
    # RETURN the validated plan.
    @app.post('/api/roadmap')
    def roadmap():
        data = body()
        role = field(data, 'role', 160, 2)
        cv = field(data, 'cv', 30000)
        gaps = field(data, 'gaps', 12000)
        feedback = field(data, 'feedback', 18000)
        if not any((cv, gaps, feedback)):
            raise ValueError('Add your CV, skill gaps, or interview feedback to personalize the plan.')
        weeks, hours = data.get('weeks', 4), data.get('hours', 5)
        if type(weeks) is not int or not 1 <= weeks <= 12 or type(hours) is not int or not 1 <= hours <= 20:
            raise ValueError('Choose 1–12 weeks and 1–20 study hours per week.')
        demo = data.get('demo') is True
        if demo:
            skills = keyword_skills(gaps) or ['role fundamentals', 'clear communication', 'evidence of impact']
            schedule = []
            for week in range(1, weeks + 1):
                skill = skills[(week - 1) % len(skills)]
                activities = [{'task': f'Practice {skill} through a small {role} work sample.', 'hours': hours}]
                if hours >= 2:
                    activities = [{'task': f'Study core {skill} concepts and write a one-page explanation.', 'hours': max(1, hours // 2)},
                                  {'task': f'Create a {role} work sample demonstrating {skill}.', 'hours': hours - max(1, hours // 2)}]
                schedule.append({'week': week, 'focus': skill, 'activities': activities,
                                 'deliverable': f'One work sample and a two-minute explanation of your {skill} decisions.',
                                 'success_check': 'Explain your approach without notes and ask a peer for one improvement.',
                                 'resource_hint': f'Use official documentation or introductory materials for {skill}.'})
            result = {'summary': 'Illustrative demo plan. It rotates detected gap keywords and respects your weekly time budget; use live AI for deeper personalization.', 'weeks': schedule}
        else:
            result = generate('Build an actionable personalized learning roadmap grounded in target role, CV gaps and/or interview feedback. Return JSON {"summary":"priorities tied to supplied evidence","weeks":[{"week":1,"focus":"specific skill","activities":[{"task":"concrete task","hours":2}],"deliverable":"portfolio artifact","success_check":"observable completion criterion","resource_hint":"specific official documentation title, publisher and relevant chapter or exercise; no invented courses or URLs"}]}. Return exactly the requested number of sequential weeks. Each week must have 1–4 activities whose positive hours total no more than the weekly budget. First inventory skills evidenced in the CV, including Playwright, K6 and CI/CD if present. Explain in summary which skills are already evidenced and which gaps this plan targets. Do not repeat beginner training for evidenced skills unless explicitly requested; use advanced extensions, a diagnostic challenge or a new gap instead. Tie each task to a supplied gap or feedback item, avoid duplicate activities across weeks, and specify a concrete official documentation chapter and exercise in resource_hint. For every topic at five hours or fewer, choose one small existing documentation example or single-file fixture, budget setup, limit the exercise to one scenario, and allow an explicitly unexecuted design if tooling is blocked. Do not combine language setup, Selenium and language fundamentals in one week, or require a microservices deployment to learn resilience. For weekly budgets of five hours or fewer, mobile testing must cover only one platform and one interaction/assertion on an existing sample app. Include setup time and a fallback test sketch if tooling is blocked; defer the second platform, CI and full frameworks. Sequence prerequisites before advanced work. Do not assume missing CV evidence proves a lack of skill.',
                              {'role': role, 'cv': cv, 'gaps': gaps, 'interview_feedback': feedback, 'weeks': weeks, 'hours_per_week': hours})
        text(result, 'summary')
        schedule = array(result, 'weeks', 12)
        if len(schedule) != weeks:
            raise ValueError('The AI returned a different plan length. Please retry.')
        for i, week in enumerate(schedule, 1):
            if type(obj(week).get('week')) is not int or week['week'] != i:
                raise ValueError('The AI returned an invalid week order. Please retry.')
            scope_mobile_week(week, hours)
            raw_activities=week.get('activities')
            if isinstance(raw_activities,list) and raw_activities and sum(number(obj(a).get('hours'), .25, hours) for a in raw_activities)>hours:
                raise ValueError('The plan exceeds your weekly time budget. Please retry.')
            scope_small_week(week, hours)
            for key in ('focus', 'deliverable', 'success_check', 'resource_hint'):
                text(week, key)
            activities = array(week, 'activities', 4)
            if not activities or sum(number(obj(a).get('hours'), .25, hours) for a in activities) > hours:
                raise ValueError('The plan exceeds your weekly time budget. Please retry.')
            for activity in activities:
                text(activity, 'task')
            week['resource_links'] = learning_resources(week)
            if week['resource_links']:
                week['resource_hint'] = '; '.join(link['title'] for link in week['resource_links'])
            week['resource_status'] = 'matched' if week['resource_links'] else 'No matching curated direct link yet; use the named resource recommendation.'
        return jsonify(plan=result, demo=demo)

    # PSEUDOCODE: COMPANY PREPARATION
    # VALIDATE company and role.
    # RETURN a generic demo brief or research the company online.
    # FILTER company-value and topic citations against retrieved sources.
    # RETURN the brief and suggested practice questions, not confirmed employer questions.
    @app.post('/api/company-prep')
    def company_prep():
        data = body()
        company = field(data, 'company', 160, 2)
        role = field(data, 'role', 160, 2)
        candidate_cv = field(data, 'cv', 30000)
        demo = data.get('demo') is True
        if demo:
            result = {'overview': f'Demo practice brief for {company}. No company research was performed; the topics below are generic role practice.', 'values': [],
                      'topics': [{'topic': 'Role-specific problem solving', 'reason': f'Prepare a real example of solving a problem as a {role}.', 'source_url': None},
                                 {'topic': 'Collaboration', 'reason': 'Explain a time you worked through a disagreement.', 'source_url': None}],
                      'questions': [f'What interests you in a {role} opportunity at {company}?', 'Walk me through a difficult project and your personal contribution.', 'What would you want to learn about the team before joining?']}
            refs = {}
        else:
            result = research('Research the named company using web search, preferring its official imprint/legal, about, values, product and careers pages. Research identity and culture separately: after the legal/imprint lookup, search official careers/team and values/about pages explicitly. Do not stop at the imprint. Values require an explicit company statement; practice topics may be inferred from sourced engineering/product responsibilities but must be labelled as suggested practice, not company values. If official pages cannot be retrieved, disclose the coverage limit instead of guessing. Resolve the exact company entity before any parent or founding claim; never expand an abbreviation from memory. Return identity_facts as an array of objects with kind legal_name or parent, value copied exactly from the source, source_quote as an exact contiguous passage establishing that fact, and source_url from retrieved first-party pages. Keep parent and identity statements out of values, topics and questions; they are verified separately. Questions should rehearse the target role, using its actual responsibilities, rather than merely ask generic questions about the company. Return JSON {"identity_facts":[{"kind":"legal_name|parent","value":"exact source text","source_quote":"exact source passage","source_url":"exact first-party URL"}],"overview":"short sourced company overview","values":[{"value":"company value","evidence":"short paraphrase","source_url":"exact supporting source URL"}],"topics":[{"topic":"practice competency","reason":"why this is relevant, citing source context","source_url":"exact supporting source URL"}],"questions":["suggested practice question"]}. Provide up to 4 values, 5 topics and 5 questions. Never present suggested questions as leaked, confirmed or actual interview questions. Distinguish sourced facts from inferred practice suggestions. Do not invent facts if research is thin. Include a source_url only from retrieved sources.',
                              {'company': company, 'role': role}, web=True)
            refs = sources(result)
            from company_facts import verified_company
            result['identity_facts'], result['overview'] = verified_company(result, company, refs)
            result['identity_verified'] = bool(result['identity_facts'])
            if not result.get('values'):
                from company_facts import culture_values
                result['values'],result['culture_checks']=culture_values(company,refs)
        text(result, 'overview')
        for key, title, detail in [('values', 'value', 'evidence'), ('topics', 'topic', 'reason')]:
            cleaned = []
            items = result.get(key, [])
            for item in items[:8] if isinstance(items, list) else []:
                try:
                    text(item, title, 250)
                    text(item, detail)
                except ValueError:
                    continue
                if key == 'values':
                    from company_facts import substantive_value
                    if not substantive_value(item[title]):
                        continue
                link = url(item.get('source_url'))
                if not demo and source_key(link) not in {source_key(ref) for ref in refs}:
                    continue
                if not demo and re.search(r'subsidiary|parent (?:company|organization)|owned by|company of', item[title] + ' ' + item[detail], re.I):
                    continue
                claim = {title: item[title], detail: item[detail], 'source_url': link or None}
                if not demo:
                    brand = re.sub(r'[^a-z0-9]', '', company.split(',')[0].casefold())
                    host = re.sub(r'[^a-z0-9]', '', (urlsplit(link).hostname or '').removeprefix('www.').split('.')[0])
                    claim['basis'] = 'Employer-named source; policy applicability unverified' if len(brand)>=3 and brand in host else 'External or parent-company context; not verified for this employer'
                    claim['applicability'] = f'Applicability to {company} and the intended employment country has not been independently established. Ask the recruiter whether this statement or benefit applies to this specific role and contract.'
                cleaned.append(claim)
            result[key] = cleaned
        if not demo:
            result['research_coverage'] = ('Company values are linked to retrieved sources.' if result['values'] else
                'No supported company values were retrieved. This is a research coverage limit, not evidence that the company has no stated values.')
            if not result['topics']:
                result['topics'] = [
                    {'topic': 'Risk-based testing and test reliability' if re.search(r'qa|test|quality', role, re.I) else f'{role}: project decisions',
                     'reason': 'Role-based practice suggestion: explain a real decision, alternatives and evidence. Company-specific relevance was not verified.',
                     'source_url': None, 'basis': 'Role-based suggestion; not a researched company fact'},
                    {'topic': 'Collaboration and individual contribution',
                     'reason': 'Prepare a real example of working through a disagreement and distinguish your contribution from the team outcome.',
                     'source_url': None, 'basis': 'Role-based suggestion; not a researched company fact'}]
        result['questions'] = rehearsal_questions(candidate_cv, role)
        result['question_basis'] = 'Candidate rehearsal based on supplied CV excerpts and target role; not confirmed employer questions.' if candidate_cv else 'Role-focused candidate rehearsal; add CV context to personalize the questions.'
        if not demo:
            # Only source-checked identity, never raw model narrative, becomes interview context.
            result['practice_context'] = result['overview'] + '\nSuggested candidate rehearsal (not confirmed employer questions):\n' + '\n'.join(result['questions'])
        result.pop('_sources', None)
        used={source_key(item.get('source_url')) for key in ('identity_facts','values','topics') for item in result.get(key,[]) if item.get('source_url')}
        return jsonify(brief=result, sources=[item for link,item in refs.items() if source_key(link) in used],
                       background_sources=[item for link,item in refs.items() if source_key(link) not in used], demo=demo, researched_at=None if demo else datetime.now(timezone.utc).isoformat())

