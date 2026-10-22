"""Conservative, source-quoted workplace eligibility checks (not immigration advice)."""
import re
import unicodedata


def normalized(value):
    return ' '.join(unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode().casefold().split())


ALIASES = {
    'spain': ('spain', 'espana', 'spanien', 'es', 'esp'),
    'germany': ('germany', 'deutschland', 'alemania', 'de'),
    'france': ('france', 'frankreich', 'francia', 'fr'),
    'greece': ('greece', 'grecia', 'griechenland', 'gr'),
    'eu': ('eu', 'european union'), 'europe': ('europe', 'europa'),
}


def canonical(value):
    value = normalized(value).strip(' ,')
    return next((key for key, names in ALIASES.items() if value in names), value)


def geography_matches(requested, place):
    requested_parts = [canonical(part) for part in requested.split(',') if part.strip()]
    place_parts = [canonical(part) for part in place.split(',') if part.strip()]
    # A city+country source supports either its city or its country, with word boundaries.
    return bool(requested_parts and all(part in place_parts for part in requested_parts))


def location_matches(requested, evidence, visible, *, workplace_field=False):
    """Require an exact source quote and explicit workplace geography.

    A remote label, office footer, or candidate's citizenship alone cannot establish
    that an employer permits work from a particular country.
    """
    if not requested.strip():
        return None
    if not isinstance(evidence, dict):
        return None
    quote, place, mode = (evidence.get(key, '') for key in ('quote', 'place', 'mode'))
    if not all(isinstance(value, str) and value.strip() for value in (quote, place, mode)):
        return None
    if mode not in ('onsite', 'hybrid', 'remote', 'unspecified') or len(quote) > 1200:
        return None
    q, p = normalized(quote), normalized(place)
    if q not in normalized(visible) or not re.search(r'(?<!\w)' + re.escape(p) + r'(?!\w)', q):
        return None
    # Do not interpret exclusions, relocation or nationality as working permission.
    if re.search(r'\b(except|excluding|not available|not eligible|not permitted|not allowed|cannot|relocat\w*|citizen\w*|nationality|visa|sponsor\w*)\b', q):
        return None
    if re.search(r'\b(office|offices|headquarters|customers|clients)\b', q):
        return None
    remote = re.search(r'\b(remote|remotely|remoto|remota|teletrabajo|anywhere|worldwide)\b', q)
    hybrid = re.search(r'\b(hybrid|hibrido|hibrida)\b', q)
    if not workplace_field and not re.search(r'\b(location|based|work|working|remote|remotely|remoto|remota|teletrabajo|hybrid|hibrido|onsite|on-site|anywhere|worldwide)\b', q):
        return None
    if mode == 'remote' and (not remote or hybrid):
        return None
    if mode != 'remote' and remote and not hybrid:
        return None
    choices = re.split(r'\s+(?:or|oder|o)\s+|[;/]', normalized(requested))
    matched = False
    for choice in choices:
        requires_remote = bool(re.search(r'\bremote\b', choice))
        destination = canonical(re.sub(r'\bremote\b', '', choice).strip())
        if requires_remote and mode != 'remote':
            continue
        if not destination:
            matched = mode == 'remote'
        elif geography_matches(destination, p):
            matched = True
        elif destination == 'spain' and mode == 'remote' and canonical(p) in ('eu', 'europe'):
            # Only explicit regional permission, never an employer office address.
            matched = bool(re.search(r'(?:remote|work|based|anywhere)\s+(?:(?:from|in|across|within|throughout)\s+)?(?:the\s+)?(?:eu|europe|european union)\b', q))
        if matched:
            break
    if not matched:
        return None
    return {'quote': quote.strip(), 'place': place.strip(), 'mode': mode,
            'status': 'Employer workplace location supported by source; personal work authorization is not assessed.'}
