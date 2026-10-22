"""Keep generated replacement bullets out of review prose."""
import re

REWRITE = re.compile(r"\b(?:rewrite|rephrase|reword|before\s*/\s*after|suggested bullet|replacement bullet)\b|\breplace\b.{0,100}\bwith\b|\b(?:e\.g\.|for example)\s*[:,-]?\s*[\"'\u2018\u201c]?(?:developed|built|created|led|managed|maintained)", re.I)
ACTION = re.compile(r"^(?:I\s+)?(?:developed|built|created|designed|implemented|maintained|led|managed|owned|delivered|improved|reduced|increased)\b", re.I)
QUOTES = re.compile(r'"([^"\n]+)"|\u201c([^\u201d\n]+)\u201d|\u2018([^\u2019\n]+)\u2019|(?<!\w)\'([^\'\n]+)\'(?!\w)')


def grounded_review_prose(report, cv):
    from career_features import cv_evidence_excerpt
    def exact(value):
        try:
            cv_evidence_excerpt(cv, value)
            return True
        except ValueError:
            return False

    def unsafe(value):
        if REWRITE.search(value) and not value.startswith('Factual bullet base (original CV text):'):
            return True
        for match in QUOTES.finditer(value):
            quote = next(part for part in match.groups() if part is not None).strip()
            if ACTION.search(quote) and len(quote.split()) >= 3 and not exact(quote):
                return True
        # Also catch unquoted replacement bullets and assertions of ongoing ownership.
        if ACTION.search(value.strip()) and not exact(value.strip()):
            return True
        if re.search(r'\bmaintain(?:ed|ing|s)?\b', value, re.I) and not re.search(r'\b(if|whether|consider|learn|practice|ask|confirm|evidence|verify)\b', value, re.I):
            tool = re.search(r'playwright|k6|cypress|selenium', value, re.I)
            evidence = [line for line in cv.splitlines() if not tool or tool[0].casefold() in line.casefold()]
            if not any(re.search(r'\bmaintain(?:ed|ing|s)?\b', line, re.I) for line in evidence):
                return True
        return False

    for key in ('strengths', 'improvements', 'next_steps'):
        report[key] = [value for value in report[key] if not unsafe(value)]
    for key in ('summary', 'score_explanation'):
        parts = re.split(r'(?<=[.!?])\s+', report[key])
        report[key] = ' '.join(part for part in parts if not unsafe(part)).strip() or 'Use the original CV evidence below. New responsibilities or achievements require your confirmation; this score is subjective practice feedback.'
    return report
