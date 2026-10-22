import re
"""Evidence coaching; personal memory stays in the browser."""


def narrative_sentences(source):
    sentences=[part.strip() for part in re.findall(r'[^\n]+?(?:[.!?](?=\s|$)|$)',source) if part.strip()]
    return [part for part in sentences if not re.search(r'^(?:please\b|do not\b|don.t\b|never\b|avoid\b|without inventing\b)|\b(?:don.t|do not|never) (?:add|invent|include|make up)\b',part,re.I)]


def extractive_story(source):
    sentences=narrative_sentences(source)
    task=next((part for part in sentences if re.search(r'\bI (?:owned|was responsible|was tasked|needed|had to)\b',part,re.I)), '')
    action=next((part for part in sentences if re.search(r'\bI (?:built|implemented|automated|created|designed|tested|investigated|developed|collaborated|introduced)\b',part,re.I)), '')
    situation=next((part for part in sentences if part not in (task,action) and not re.search(r'\b(?:results?|outcome|measured|quantified|fell from|reduced)\b',part,re.I)), '')
    return dict(situation=situation, task=task, action=action, result='')


# PSEUDOCODE: STAR STORY STRUCTURING
# REGISTER the evidence endpoint and validate source experience and skill.
# IN demo mode, return an editable STAR template.
# OTHERWISE ask for source quotations for Situation, Task, Action and Result.
# REJECT any nonempty field that is not an exact source excerpt.
# RETURN grounded fields and a list of missing sections for user review.
def register_coaching(app, generate, body, field):
    @app.post('/api/evidence')
    def evidence():
        data = body()
        source = field(data, 'source', 12000, 40)
        skill = field(data, 'skill', 160, 2)
        keys = ('situation', 'task', 'action', 'result')
        if data.get('demo') is True:
            return dict(story=dict(situation=source, task='[Add your responsibility]',
                                   action='[Add what you personally did]', result='[Add a verified outcome]'),
                        demo=True, missing=['Task', 'Action', 'Result'])
        result = generate('Structure the supplied experience as a STAR interview story. '
                          'Return {"story":{"situation":"...","task":"...","action":"...","result":"..."}}. '
                          'Each nonempty field MUST be an exact contiguous quotation from source, preserving spelling and punctuation. '
                          'Use empty strings for missing evidence. Never invent metrics, actions, or responsibilities.',
                          dict(source=source, skill=skill))
        story = result.get('story')
        # Keep an extractive draft usable when model fields fail the evidence guard.
        # Do not repair facts, infer a Result, or silently turn rejected prose into evidence.
        fallback = not isinstance(story, dict)
        clean = {}
        if not fallback:
            for key in keys:
                value = story.get(key, '')
                if not isinstance(value, str) or len(value) > 12000 or (value.strip() and value.strip() not in source):
                    fallback = True
                    break
                clean[key] = value.strip()
                if value.strip() and re.search(r'\b(?:do not|don.t|never) (?:add|invent|include|make up)\b',value,re.I):
                    clean[key]=next(iter(narrative_sentences(value)), '')
                    fallback=True
            fallback = fallback or not any(clean.values())
            fallback = fallback or (clean.get('situation') == source and not any(clean.get(key) for key in ('task','action','result')))
        if not fallback and re.search(r'no (?:measured|quantified|verified)|not (?:measured|quantified)|do not have.{0,50}results?', clean['result'], re.I):
            clean['result'] = ''
        if fallback:
            clean = extractive_story(source)
        return dict(story=clean, missing=[key.title() for key in keys if not clean[key]], demo=False,
                    fallback=fallback, recovery_notice='Some AI fields could not be verified. An extractive fallback preserves source sentences where their role is explicit. Review the draft: what was your responsibility, what did you do, and what outcome can you support? Missing evidence stays blank; no Result was invented.' if fallback else None)
