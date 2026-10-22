import json
import time
import unittest
from unittest.mock import patch, Mock
import job_links


class JobLinkTests(unittest.TestCase):
    def setUp(self):
        self.job = {'url': 'https://employer.test/jobs/qa-42', 'title': 'QA Engineer'}

    def check(self, replies):
        with patch('job_links.fetch_page', side_effect=replies) as fetch:
            result = job_links.check_link(self.job, time.monotonic() + 4)
        return result, fetch

    def test_missing_and_closed_offers_are_removed(self):
        for reply in [(404, None, '', b''), (410, None, '', b''),
                      (200, None, 'text/html', b'<h1>This position has been filled</h1>')]:
            with self.subTest(reply=reply):
                self.assertIsNone(self.check([reply])[0])

    def test_careers_redirect_is_removed_without_fetching_general_page(self):
        result, fetch = self.check([(302, '/careers', '', b'')])
        self.assertIsNone(result)
        self.assertEqual(fetch.call_count, 1)

    def test_matching_posting_expiry_and_unconfirmed_pages(self):
        posting = {'@type': 'JobPosting', 'title': 'QA Engineer', 'validThrough': '2000-01-01'}
        def page(data):
            return (200, None, 'text/html', ('<script type="application/ld+json">' + json.dumps(data) + '</script>').encode())
        self.assertIsNone(self.check([page(posting)])[0])
        del posting['validThrough']
        self.assertEqual(self.check([page(posting)])[0]['link_status'], 'posting_found')
        posting['title'] = 'Unrelated role'
        self.assertEqual(self.check([page(posting)])[0]['link_status'], 'unconfirmed')
        self.assertEqual(self.check([(403, None, 'text/html', b'Blocked')])[0]['link_status'], 'unconfirmed')

    def test_timeout_keeps_original_link_honestly_unconfirmed(self):
        with patch('job_links.fetch_page', side_effect=TimeoutError()):
            result = job_links.check_job_links([self.job])
        self.assertEqual(result, [{**self.job, 'link_status': 'unconfirmed'}])

    def test_offer_text_preserves_requirements_beyond_summary_and_discloses_limits(self):
        requirements='Java or Kotlin. SQL. Service virtualization. Distributed systems. CI/CD. Mentoring. Fluent English. '
        html=('<h1>QA Engineer</h1><p>'+requirements*3+'</p><button>Apply</button>').encode()
        result,_=self.check([(200,None,'text/html',html)])
        self.assertIn('Service virtualization',result['offer_text'])
        self.assertIn('Fluent English',result['offer_text'])
        self.assertEqual(result['offer_source_url'],self.job['url'])
        self.assertIn('completeness must be checked',result['offer_text_status'])

    def test_only_public_https_addresses_are_requested(self):
        for link in ('http://public.test/job', 'https://user:pass@public.test/job', 'https://public.test:8080/job'):
            with self.subTest(link=link), self.assertRaises(ValueError):
                job_links.public_target(link)
        for address in ('127.0.0.1', '10.0.0.1', '169.254.169.254', '::1'):
            with patch('job_links.socket.getaddrinfo', return_value=[(0, 0, 0, '', (address, 443))]), self.assertRaises(ValueError):
                job_links.public_target('https://public.test/job')
        with patch('job_links.socket.getaddrinfo', return_value=[(0, 0, 0, '', ('8.8.8.8', 443))]):
            self.assertEqual(job_links.public_target('https://public.test/job?id=42'), ('public.test', '8.8.8.8', '/job?id=42'))

    def test_fetch_pins_vetted_ip_and_keeps_hostname_tls_validation(self):
        response = Mock(status=200)
        response.getheader.side_effect = lambda name, default=None: 'text/html' if name == 'Content-Type' else default
        response.read1.side_effect = [b'<h1>QA Engineer</h1>', b'']
        connection = Mock()
        connection.getresponse.return_value = response
        with patch('job_links.public_target', return_value=('employer.test', '8.8.8.8', '/jobs/42')), patch('job_links.socket.create_connection') as connect, patch('job_links.ssl.create_default_context') as context, patch('job_links.http.client.HTTPSConnection', return_value=connection):
            result = job_links.fetch_page(self.job['url'], time.monotonic() + 4)
        self.assertEqual(connect.call_args.args[0], ('8.8.8.8', 443))
        self.assertEqual(context.return_value.wrap_socket.call_args.kwargs['server_hostname'], 'employer.test')
        self.assertEqual(result[3], b'<h1>QA Engineer</h1>')
        connection.close.assert_called_once()

    def test_matching_application_without_structured_metadata(self):
        reply = (200, None, 'text/html', b'<h1>QA Engineer</h1><a href="/application/42">Jetzt bewerben</a>')
        self.assertEqual(self.check([reply, (200, None, 'text/html', b'<h1>QA Engineer</h1><form><button>Apply</button></form>')])[0]['link_status'], 'application_found')
        unrelated = (200, None, 'text/html', b'<h1>Other role</h1><button>Apply</button>')
        self.assertEqual(self.check([unrelated])[0]['link_status'], 'unconfirmed')
        hidden = (200, None, 'text/html', b'<script>QA Engineer</script><button>Apply</button>')
        self.assertEqual(self.check([hidden])[0]['link_status'], 'unconfirmed')

    def test_application_links_follow_redirects_and_keep_requisition_identity(self):
        direct = 'https://job-boards.greenhouse.io/dkbcodefactory/jobs/8004226003'
        source = 'https://jobseek.test/jobs/dkb-qa'
        source_page = ('<h1>QA Engineer</h1><a href="/apply/dkb">Apply on employer website</a>').encode()
        final_page = b'<h1>QA Engineer</h1><button>Apply</button>'
        replies = [(200, None, 'text/html', source_page), (302, direct + '?ref=jobseek.dev', '', b''), (200, None, 'text/html', final_page)]
        with patch('job_links.fetch_page', side_effect=replies) as fetch:
            result = job_links.check_link({**self.job, 'url': source}, time.monotonic() + 4)
        self.assertEqual(job_links.application_key(result['application_url']), direct)
        self.assertEqual(result['url'], source)
        self.assertEqual(fetch.call_count, 3)
        other = direct.replace('8004226003', '8004226004')
        self.assertNotEqual(job_links.application_key(other), job_links.application_key(direct))
        self.assertNotEqual(job_links.application_key('https://employer.test/job?id=1'), job_links.application_key('https://employer.test/job?id=2'))

    def test_fragment_apply_buttons_do_not_trigger_another_fetch(self):
        reply = (200, None, 'text/html', b'<h1>QA Engineer</h1><a href="#application">Apply</a>')
        result, fetch = self.check([reply])
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(result['application_url'], self.job['url'])

    def test_application_redirect_cannot_fetch_private_destination(self):
        html = b'<h1>QA Engineer</h1><a href="https://127.0.0.1/jobs/private">Apply</a>'
        def fetch(link, deadline):
            if link == self.job['url']:
                return 200, None, 'text/html', html
            job_links.public_target(link)
        with patch('job_links.fetch_page', side_effect=fetch), patch('job_links.socket.getaddrinfo', return_value=[(0,0,0,'',('127.0.0.1',443))]):
            result = job_links.check_job_links([self.job])
        self.assertNotIn('application_url', result[0])
