"""Company identity facts checked against retrieved first-party pages."""
import re
import time
import json
from pathlib import Path
from datetime import date
from urllib.parse import urlsplit, urljoin
from job_links import Page, fetch_page


def normalized(value):
    return ' '.join(value.casefold().split())


def substantive_value(value):
    """Navigation and calls to action are not employer values."""
    if not isinstance(value,str):
        return False
    label=re.sub(r'[^a-z0-9 ]','',normalized(value)).strip()
    if re.match(r'^(?:learn|read|find out|discover|see|view|show)\s+(?:more|about)\b',label):
        return False
    return bool(label) and not re.fullmatch(r'(?:learn|read|find out|discover|see|view|show)(?: more| all| our values)?|click here|explore|our values|values|culture|apply(?: now)?|join us|contact(?: us)?|about(?: us)?',label)


def culture_values(company, refs):
    """Try an explicit first-party culture page; report blocking, never fill from a parent."""
    brand=re.sub(r'[^a-z0-9]','',company.split(',')[0].casefold())
    links=[]
    for link in refs:
        parts=urlsplit(link)
        host=parts.hostname or ''
        if len(brand)>=3 and brand in re.sub(r'[^a-z0-9]','',host.removeprefix('www.').split('.')[0]):
            target='https://'+host+'/culture'
            if target not in links:
                links.append(target)
    attempts=[]
    deadline=time.monotonic()+4
    for link in links[:2]:
        try:
            status,redirect,kind,body=fetch_page(link,deadline)
            if status!=200 or 'html' not in kind.lower():
                attempts.append({'url':link,'status':f'Not retrieved (HTTP {status}); no values inferred.'})
                continue
            page=Page();page.feed(body.decode('utf-8',errors='replace'))
            parts=[' '.join(part.split()) for part in page.parts if part.strip()]
            actions={normalized(item) for item in page.actions if item.strip()}
            start=next((i for i,part in enumerate(parts) if re.search(r'our values|what we value|values guide',part,re.I)),None)
            values=[]
            if start is not None:
                for part in parts[start+1:start+45]:
                    if normalized(part) not in actions and substantive_value(part) and 10<=len(part)<=240 and re.search(r'people|customer|learn|experiment|responsib',part,re.I):
                        values.append({'value':part,'evidence':part,'source_url':link})
                        if len(values)==4:
                            break
            attempts.append({'url':link,'status':'Retrieved; explicit value statements extracted.' if values else 'Retrieved; no explicit value section could be safely extracted.'})
            if values:
                refs[link]={'url':link,'title':'Official culture: displayed value statements'}
                return values,attempts
        except Exception:
            attempts.append({'url':link,'status':'Retrieval unavailable or timed out; no values inferred.'})
    return [],attempts


def verified_company(result, company, refs):
    from career_features import source_key
    # Restrict identity verification to company-named first-party domains, never aggregators.
    brand = re.sub(r'[^a-z0-9]', '', company.split(',')[0].casefold())
    links = [link for link in refs if len(brand) >= 3 and brand in re.sub(r'[^a-z0-9]', '', (urlsplit(link).hostname or '').removeprefix('www.').split('.')[0])]
    links.sort(key=lambda link: 0 if re.search(r'imprint|impressum|legal', link, re.I) else 1)
    pages = {}
    deadline = time.monotonic() + 5
    for original in links[:3]:
        link = original
        try:
            for _ in range(3):
                status, redirect, kind, body = fetch_page(link, deadline)
                if status in (301,302,303,307,308) and redirect:
                    target = urljoin(link, redirect)
                    if (urlsplit(target).hostname or '').removeprefix('www.') != (urlsplit(original).hostname or '').removeprefix('www.'):
                        break
                    link = target
                    continue
                if status == 200 and 'html' in kind.lower() and len(body) <= 512000:
                    page = Page(); page.feed(body.decode('utf-8', errors='replace'))
                    pages[source_key(original)] = ' '.join(page.parts)
                break
        except Exception:
            continue
    facts = []
    proposed = result.get('identity_facts', [])
    proposed = proposed[:6] if isinstance(proposed, list) else []
    for fact in proposed:
        if not isinstance(fact, dict) or fact.get('kind') not in ('legal_name','parent'):
            continue
        value, quote, link = (fact.get(key, '') for key in ('value','source_quote','source_url'))
        if not all(isinstance(item,str) and item.strip() for item in (value,quote,link)):
            continue
        page = pages.get(source_key(link), '')
        if len(quote)>1000 or normalized(quote) not in normalized(page) or normalized(value) not in normalized(quote):
            continue
        if fact['kind']=='legal_name' and brand not in re.sub(r'[^a-z0-9]', '', value.casefold()):
            continue
        if fact['kind']=='parent' and not re.search(r'company of|subsidiary of|owned by|parent', quote, re.I):
            continue
        facts.append({'kind':fact['kind'],'value':value.strip(),'source_quote':quote.strip(),'source_url':link})
    # Extract a plainly labeled parent directly when a model confuses an abbreviation.
    parents = []
    for link, page in pages.items():
        match = re.search(r'\b(?:a company of|subsidiary of|owned by)\s+([A-Z][A-Za-z &.-]{2,90}?\b(?:AG|GmbH|Inc\.?|Ltd\.?|PLC|SE))\b', page, re.I)
        if match:
            parents.append({'kind':'parent','value':match[1].strip(),'source_quote':match[0].strip(),'source_url':link})
    if parents:
        facts = [fact for fact in facts if fact['kind']!='parent'] + parents[:1] if len({normalized(fact['value']) for fact in parents})==1 else [fact for fact in facts if fact['kind']!='parent']
    unique = {fact['kind']: fact for fact in facts}
    # A dated, manually reviewed first-party reference remains usable when a site blocks bots.
    reviewed = json.loads(Path(__file__).with_name('company_identities.json').read_text(encoding='utf-8')).get(brand)
    if 'parent' not in unique and reviewed and 0 <= (date.today() - date.fromisoformat(reviewed['reviewed_at'])).days <= 30:
        for kind in ('legal_name', 'parent'):
            unique.setdefault(kind, {'kind':kind,'value':reviewed[kind], 'source_url':reviewed['source_url'],
                            'source_quote':reviewed['source_quote'] if kind=='parent' else reviewed['legal_name'],
                            'verification':'reviewed_reference', 'reviewed_at':reviewed['reviewed_at']})
        refs[reviewed['source_url']] = {'url':reviewed['source_url'],'title':'Official imprint (reference reviewed ' + reviewed['reviewed_at'] + ')'}
    overview = ' '.join(('Company: ' if kind=='legal_name' else 'Parent organization: ') + fact['value'] + '.' for kind,fact in unique.items())
    if unique and any(fact.get('verification')=='reviewed_reference' for fact in unique.values()):
        overview += ' Official reference reviewed ' + reviewed['reviewed_at'] + '; live parent verification unavailable.'
    if not overview:
        overview = 'Company identity and parent organization could not be independently verified from the retrieved first-party pages. No affiliation is assumed. Review the sources before using company facts in an interview.'
    return list(unique.values()), overview
