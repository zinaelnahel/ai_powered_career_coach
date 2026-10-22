"""Bounded public-HTTPS checks; a reachable page is not proof of an open vacancy."""
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import datetime, timezone
from html.parser import HTMLParser
import http.client
import ipaddress
import json
import re
import socket
import ssl
import time
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qsl, urlencode

LINK_POOL = ThreadPoolExecutor(max_workers=16)

class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts, self.scripts, self.script = [], [], None
        self.actions = []
        self.anchors = []
        self.anchor = None
        self.hidden = 0
        self.action_tag = None
        self.in_heading = False
        self.heading = []
        self.after_heading = []
        self.heading_done = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'h1' and not self.heading_done:
            self.in_heading = True
        if tag in ('script', 'style'):
            self.hidden += 1
        if tag == 'a':
            self.anchor = {'href': attrs.get('href', ''), 'text': attrs.get('aria-label', '')}
            self.anchors.append(self.anchor)
        if tag in ('a', 'button'):
            self.action_tag = tag
        if tag in ('a', 'form', 'button', 'input'):
            self.actions.append(' '.join(attrs.get(key, '') for key in ('href', 'action', 'value', 'aria-label')))
        if tag == 'script' and attrs.get('type', '').lower() == 'application/ld+json':
            self.script = []

    def handle_data(self, data):
        if self.script is not None:
            self.script.append(data)
        elif not self.hidden:
            self.parts.append(data)
            if self.anchor is not None:
                self.anchor['text'] += ' ' + data
            if self.in_heading:
                self.heading.append(data)
            elif self.heading_done and len(self.after_heading) < 12 and data.strip():
                self.after_heading.append(data.strip())
            if self.action_tag:
                self.actions.append(data)

    def handle_endtag(self, tag):
        if tag == 'a':
            self.anchor = None
        if tag == 'h1' and self.in_heading:
            self.in_heading = False
            self.heading_done = True
        if tag == self.action_tag:
            self.action_tag = None
        if tag in ('script', 'style'):
            self.hidden = max(0, self.hidden - 1)
        if tag == 'script' and self.script is not None:
            self.scripts.append(''.join(self.script))
            self.script = None


def public_target(link):
    parts = urlsplit(link)
    if parts.scheme != 'https' or not parts.hostname or parts.username or parts.password or parts.port not in (None, 443):
        raise ValueError('Only public HTTPS links can be checked.')
    host = parts.hostname.encode('idna').decode()
    addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise ValueError('Non-public addresses cannot be checked.')
    return host, addresses[0][4][0], (parts.path or '/') + ('?' + parts.query if parts.query else '')


def fetch_page(link, deadline):
    host, address, path = public_target(link)
    remaining = min(3, deadline - time.monotonic())
    if remaining <= 0:
        raise TimeoutError()
    # Pin the vetted address while preserving TLS certificate/hostname checks.
    connection = http.client.HTTPSConnection(host, timeout=remaining)
    try:
        raw = socket.create_connection((address, 443), timeout=remaining)
        try:
            connection.sock = ssl.create_default_context().wrap_socket(raw, server_hostname=host)
        except Exception:
            raw.close()
            raise
        connection.request('GET', path, headers={'User-Agent': 'CareerDojo-LinkCheck/1.0', 'Accept': 'text/html', 'Accept-Encoding': 'identity'})
        response = connection.getresponse()
        chunks, size = [], 0
        while size < 512_001:
            if time.monotonic() >= deadline:
                raise TimeoutError()
            chunk = response.read1(min(65_536, 512_001 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
        return response.status, response.getheader('Location'), response.getheader('Content-Type', ''), b''.join(chunks)
    finally:
        connection.close()


def postings(value):
    if isinstance(value, list):
        for item in value:
            yield from postings(item)
    elif isinstance(value, dict):
        types = value.get('@type', [])
        if types == 'JobPosting' or isinstance(types, list) and 'JobPosting' in types:
            yield value
        for item in value.values():
            if isinstance(item, (dict, list)):
                yield from postings(item)


class CheckedJobs(list):
    """Listings plus non-sensitive filtering counts for the search UI."""
    pass


def header_evidence(job, page):
    from job_locations import normalized, location_matches
    if normalized(' '.join(page.heading)) != normalized(job['title']):
        return None
    for value in page.after_heading[:4]:
        if len(value) > 120:
            continue
        mode = 'remote' if re.search(r'\bremote\b', value, re.I) else 'hybrid' if re.search(r'\bhybrid\b', value, re.I) else 'unspecified'
        # Only a short location value adjacent to the matching job heading.
        place = re.sub(r'\b(?:remote|hybrid|onsite|on-site)\b|[()]', '', value, flags=re.I).strip(' ,-')
        evidence = location_matches(job['_requested_location'], {'quote': value, 'place': place, 'mode': mode}, value, workplace_field=True)
        if evidence:
            return evidence
    return None


def application_key(value):
    """Keep requisition IDs while removing known tracking parameters."""
    parts = urlsplit(value)
    host = (parts.hostname or '').lower()
    if host == 'boards.greenhouse.io':
        host = 'job-boards.greenhouse.io'
    tracking = {'gh_src', 'ref'} if host == 'job-boards.greenhouse.io' else set()
    query = [(key, val) for key, val in parse_qsl(parts.query, keep_blank_values=True)
             if not key.lower().startswith('utm_') and key.lower() not in tracking]
    return urlunsplit((parts.scheme, host, parts.path.rstrip('/'), urlencode(sorted(query)), ''))


def application_target(page, link):
    from career_features import job_detail_url, url
    current = application_key(link)
    for anchor in page.anchors:
        if not re.search(r'\b(apply|application|bewerben|bewerbung|solicitar|postular)\b', anchor['text'], re.I):
            continue
        href = anchor['href']
        if not href or href.startswith(('#', 'mailto:', 'javascript:')):
            continue
        target = url(urljoin(link, href))
        if target and job_detail_url(target) and application_key(target) != current:
            return target
    return None


def check_link(job, deadline, audit=None):
    from career_features import job_detail_url
    audit = audit if audit is not None else {}
    def reject(reason):
        audit['reason'] = reason
        return None
    link = job['url']
    visited = set()
    def checked(status):
        return {**job, 'link_status': status, 'application_url': link}
    for _ in range(4):
        if application_key(link) in visited:
            return checked('unconfirmed')
        visited.add(application_key(link))
        status, redirect, content_type, body = fetch_page(link, deadline)
        if status in (404, 410):
            return reject('closed_or_missing')
        if status in (301, 302, 303, 307, 308) and redirect:
            link = urljoin(link, redirect)
            if not job_detail_url(link):
                return reject('general_page')
            continue
        if status != 200 or 'html' not in content_type.lower() or len(body) > 512_000:
            audit['reason'] = 'page_unavailable'
            return checked('unconfirmed')
        if not job_detail_url(link):
            return reject('general_page')
        page = Page()
        page.feed(body.decode('utf-8', errors='replace'))
        visible = ' '.join(page.parts)
        # Preserve source text independently of the generated card summary. Page
        # chrome and dynamic content mean completeness is never assumed.
        if not job.get('offer_text') and ' '.join(page.heading).strip() and len(visible.strip()) >= 100:
            job = {**job, 'offer_text': visible.strip()[:12000], 'offer_source_url': link,
                   'offer_text_status': 'Source page extract; completeness must be checked against the original offer.'}
        if job.get('_discover_role'):
            title = ' '.join(' '.join(page.heading).split())
            qa_title = re.search(r'\bqa\b|quality assurance|\btest(?:ing)?\b.*\bengineer', title, re.I)
            senior_required = re.search(r'\bsenior\b|\bsr\b', job['_discover_role'], re.I)
            if not title or len(title)>250 or not qa_title or (senior_required and not re.search(r'\bsenior\b|\bsr\b|\blead\b', title, re.I)):
                return reject('role_not_supported')
            job = {**job, 'title': title, 'description': 'Source page excerpt: ' + ' '.join(page.after_heading)[:1500]}
        requested = job.get('_requested_location', '')
        if requested:
            from job_locations import location_matches
            evidence = header_evidence(job, page) or location_matches(requested, job.get('location_evidence'), visible)
            if evidence is None:
                return reject('location_not_supported')
            job = {**job, 'location_verified': True, 'location_evidence': evidence}
            job['location'] = evidence['place'] + ('' if evidence['mode'] == 'unspecified' else ' (' + evidence['mode'] + ')')
        if re.search(r'(?:this|the) (?:job|position|vacancy|opening) (?:is no longer available|has (?:expired|been filled|been closed))|no longer accepting applications', visible, re.I):
            return reject('closed_or_missing')
        target = application_target(page, link)
        if target and application_key(target) not in visited:
            link = target
            continue
        for script in page.scripts:
            try:
                data = json.loads(script)
            except (ValueError, TypeError):
                continue
            for posting in postings(data):
                if str(posting.get('title', '')).casefold().strip() != job['title'].casefold().strip():
                    continue
                if posting.get('validThrough'):
                    try:
                        expiry = datetime.fromisoformat(str(posting['validThrough']).replace('Z', '+00:00'))
                        if expiry.replace(tzinfo=expiry.tzinfo or timezone.utc) < datetime.now(timezone.utc):
                            return reject('closed_or_missing')
                    except ValueError:
                        pass
                return checked('posting_found')
        normalize = lambda value: re.sub(r'[^\w]+', ' ', value.casefold()).strip()
        matching = normalize(job['title']) in normalize(visible)
        application = re.search(r'apply|bewerben|bewerbung|solicitar|postular', ' '.join(page.actions), re.I)
        if matching and application:
            return checked('application_found')
        return checked('unconfirmed')
    return checked('unconfirmed')


def check_job_links(jobs):
    if not jobs:
        return []
    deadline = time.monotonic() + 7
    audits = [{} for job in jobs]
    futures = [LINK_POOL.submit(check_link, job, deadline, audit) for job, audit in zip(jobs, audits)]
    wait(futures, timeout=7)
    results = CheckedJobs()
    results.checks = {}
    for job, future, audit in zip(jobs, futures, audits):
        try:
            value = future.result(timeout=0)
        except Exception:
            audit['reason'] = 'page_unavailable'
            value = {**job, 'link_status': 'unconfirmed'}
        reason = audit.get('reason', 'checked')
        results.checks[reason] = results.checks.get(reason, 0) + 1
        if value is not None:
            results.append(value)
    for future in futures:
        future.cancel()
    return results
