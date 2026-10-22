import time
import unittest
from unittest.mock import patch
from job_locations import location_matches
from job_links import check_job_links, check_link


class LocationTests(unittest.TestCase):
    def evidence(self, quote, place='Spain', mode='remote'):
        return dict(quote=quote, place=place, mode=mode)

    def test_spain_excludes_athens_hybrid_and_unknown_remote(self):
        for quote, place, mode in [('Hybrid, Athens', 'Athens', 'hybrid'),
                                  ('Remote', 'Spain', 'remote'),
                                  ('Remote in Greece only', 'Greece', 'remote'),
                                  ('Remote; offices in Spain', 'Spain', 'remote'),
                                  ('Remote except Spain', 'Spain', 'remote'),
                                  ('EU citizenship required', 'EU', 'remote')]:
            with self.subTest(quote=quote):
                self.assertIsNone(location_matches('Spain', self.evidence(quote, place, mode), quote))

    def test_explicit_spain_and_regional_remote_permission(self):
        for quote, place, mode in [('Remote from Spain', 'Spain', 'remote'),
                                  ('Location: Spain (Hybrid)', 'Spain', 'hybrid'),
                                  ('Work remotely from Spain', 'Spain', 'remote'),
                                  ('Remote across the European Union', 'European Union', 'remote')]:
            # The employer explicitly permits this workplace; personal legal rights remain unknown.
            with self.subTest(quote=quote):
                result = location_matches('Spanien', self.evidence(quote, place, mode), quote)
                self.assertIsNotNone(result)
                self.assertIn('personal work authorization is not assessed', result['status'])

    def test_quotes_must_exist_in_fetched_visible_page(self):
        self.assertIsNone(location_matches('Spain', self.evidence('Remote from Spain'), 'Hybrid, Athens'))
        self.assertIsNone(location_matches('Spain', None, 'Location: Spain'))

    def test_alternative_locations_and_remote_requirement(self):
        quote = 'Remote across the EU'
        evidence = self.evidence(quote, 'EU')
        self.assertIsNotNone(location_matches('Spain or remote EU', evidence, quote))
        self.assertIsNone(location_matches('remote EU', self.evidence('Location: EU', 'EU', 'onsite'), 'Location: EU'))

    def test_page_check_excludes_athens_and_forged_quote(self):
        job = dict(url='https://employer.test/jobs/42', title='Senior QA Engineer',
                   _requested_location='Spain', location_evidence=self.evidence('Remote from Spain'))
        for html in (b'<h1>Senior QA Engineer</h1><p>Hybrid, Athens</p>',
                     b'<h1>Senior QA Engineer</h1><script>Remote from Spain</script>'):
            with patch('job_links.fetch_page', return_value=(200, None, 'text/html', html)):
                self.assertIsNone(check_link(job, time.monotonic() + 4))
        html = b'<h1>Senior QA Engineer</h1><p>Remote from Spain</p><button>Apply</button>'
        with patch('job_links.fetch_page', return_value=(200, None, 'text/html', html)):
            result = check_link(job, time.monotonic() + 4)
        self.assertTrue(result['location_verified'])
        self.assertEqual(result['location'], 'Spain (remote)')

    def test_timeout_cannot_verify_location(self):
        job = dict(url='https://employer.test/jobs/42', title='QA Engineer', _requested_location='Spain')
        with patch('job_links.fetch_page', side_effect=TimeoutError()):
            self.assertFalse(check_job_links([job])[0].get('location_verified', False))

    def test_source_discovery_still_rejects_wrong_role_seniority_and_location(self):
        for title,place in [('Senior DevOps Engineer','Valencia, Spain'),('Junior QA Engineer','Valencia, Spain'),('Senior QA Engineer','Athens, Greece (Hybrid)')]:
            html=f'<h1>{title}</h1><p>{place}</p><button>Apply</button>'.encode()
            job={'url':'https://job-boards.greenhouse.io/example/jobs/42','title':'Senior QA Engineer',
                 '_discover_role':'Senior QA Engineer','_requested_location':'Spain'}
            with self.subTest(title=title,place=place),patch('job_links.fetch_page',return_value=(200,None,'text/html',html)):
                self.assertIsNone(check_link(job,time.monotonic()+7))

    def test_dkb_real_header_format_survives_country_and_city_search(self):
        from pathlib import Path
        html = (Path(__file__).parent / 'fixtures' / 'dkb_valencia.html').read_bytes()
        job = dict(url='https://job-boards.greenhouse.io/dkbcodefactory/jobs/8004226003', title='Senior QA Automation Engineer')
        for location in ('Spain', 'Spanien', 'Valencia', 'Valencia, Spain'):
            with self.subTest(location=location), patch('job_links.fetch_page', return_value=(200, None, 'text/html', html)):
                result = check_link({**job, '_requested_location': location}, time.monotonic() + 4)
                self.assertTrue(result['location_verified'])
                self.assertEqual(result['location'], 'Valencia, Spain')
                self.assertEqual(result['link_status'], 'application_found')

    def test_athens_header_does_not_qualify_as_spain_or_valencia(self):
        html = b'<h1>Senior QA Automation Engineer</h1><div>Athens, Greece (Hybrid)</div><button>Apply</button>'
        for location in ('Spain', 'Valencia'):
            job = dict(url='https://employer.test/jobs/42', title='Senior QA Automation Engineer', _requested_location=location)
            with patch('job_links.fetch_page', return_value=(200, None, 'text/html', html)):
                self.assertIsNone(check_link(job, time.monotonic() + 4))
