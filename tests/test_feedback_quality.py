import io
import os
import unittest
from unittest.mock import patch
import app as module


class FeedbackQualityTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'OPENAI_API_KEY': '', 'APP_PASSWORD': ''})
        self.env.start()
        module.limits.clear()
        self.client = module.app.test_client()
        self.cv = 'PROFILE\nSenior QA Engineer with production automation experience.\nCORE SKILLS\nTesting: Playwright, Cypress. Delivery: CI/CD, monitoring.\nEXPERIENCE\nBuilt test frameworks for 200 users.'
        self.base = {'role': 'Senior QA Engineer', 'cv': self.cv, 'description': 'QA role using test automation and CI/CD.'}
        self.report = {'score': 90, 'summary': 'Strong testing experience.', 'score_explanation': 'The existing CORE SKILLS section shows relevant automation tools, but achievements need clearer outcome evidence.', 'strengths': ['Your CORE SKILLS section groups testing and delivery tools.'], 'improvements': ['Explain one verified framework outcome.'], 'next_steps': ['Rewrite an achievement with a verified result.']}
        self.report['bullet_bases'] = [{'source_quote': 'Built test frameworks for 200 users.', 'evidence_question': 'What outcome, if any, did you measure?'}]
        self.messages = [{'role': 'assistant', 'content': 'Describe a project.'}, {'role': 'user', 'content': 'I built a testing framework for 200 users.'}]

    def tearDown(self):
        self.env.stop()

    def test_partial_interview_metadata_is_server_derived(self):
        result = self.client.post('/api/interview', json={'role': 'QA Engineer', 'messages': self.messages, 'total': 5, 'finish': True, 'demo': True, 'assessment': {'answered': 5, 'partial': False}})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json['assessment']['answered'], 1)
        self.assertEqual(result.json['assessment']['total'], 5)
        self.assertTrue(result.json['assessment']['partial'])
        self.assertIn('score_explanation', result.json['report'])

    def test_completed_interview_and_live_rationale(self):
        with patch('app.generate', return_value=self.report) as generate:
            response = self.client.post('/api/interview', json={'role': 'QA Engineer', 'messages': self.messages * 3, 'total': 3})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json['assessment']['partial'])
        self.assertEqual(response.json['assessment']['answered'], 3)
        self.assertEqual(generate.call_args.args[1]['answered_questions'], 3)
        self.assertIn('score_explanation', response.json['report'])

    def test_review_rationale_and_existing_sections_policy(self):
        with patch('app.generate', return_value=self.report) as generate:
            response = self.client.post('/api/review', json=self.base)
        self.assertEqual(response.status_code, 200)
        instructions, context = generate.call_args.args
        self.assertIn('categorized skills section', instructions)
        self.assertIn('do not recommend adding a section that is already present', instructions)
        self.assertIn('Do not diagnose bullet alignment', instructions)
        self.assertIn('Future dates explicitly marked expected', instructions)
        self.assertEqual(context['cv'], self.cv)
        self.assertIn('review_date', context)
        self.assertEqual(response.json['report']['score_explanation'], self.report['score_explanation'])

    def test_live_reports_require_a_score_explanation(self):
        report = {key: value for key, value in self.report.items() if key != 'score_explanation'}
        with patch('app.generate', return_value=report):
            for endpoint, data in [('/api/review', self.base), ('/api/interview', {'role': 'QA Engineer', 'messages': self.messages, 'total': 5, 'finish': True})]:
                response = self.client.post(endpoint, json=data)
                self.assertEqual(response.status_code, 400)
                self.assertIn('score_explanation', response.json['error'])

    def test_pdf_cleanup_removes_only_matching_edge_markers(self):
        raw = '1\nPROFILE\n2024\n1. Built a framework\n100 users\n2\nPage 1 of 3'
        cleaned = module.clean_cv_text(raw, 1, 3)
        self.assertTrue(cleaned.startswith('PROFILE'))
        self.assertNotIn('Page 1 of 3', cleaned)
        for value in ['2024', '1. Built a framework', '100 users', '\n2']:
            self.assertIn(value, cleaned)
        self.assertEqual(module.clean_cv_text('2024\nExperience\n200', 1, 3), '2024\nExperience\n200')

    def test_bullet_cleanup_and_upload_preserve_claims(self):
        raw = self.cv + '\n\x7f Improved deployment tests.\n\uf0b7 Reduced errors by 20 percent.\n1. Led testing.'
        response = self.client.post('/api/extract', data={'file': (io.BytesIO(raw.encode()), 'cv.txt')})
        self.assertEqual(response.status_code, 200)
        self.assertIn('- Improved deployment tests.', response.json['text'])
        self.assertIn('- Reduced errors by 20 percent.', response.json['text'])
        self.assertIn('1. Led testing.', response.json['text'])
        self.assertIn('200 users', response.json['text'])

    def test_review_bullet_bases_reject_invented_outcomes(self):
        self.report['bullet_bases'][0]['source_quote'] = 'Built test frameworks that reduced pre-release defects.'
        with patch('app.generate', return_value=self.report):
            result = self.client.post('/api/review', json=self.base)
        self.assertEqual(result.status_code, 400)
        self.assertIn('could not be verified', result.json['error'])

    def test_review_keeps_source_and_strips_unsolicited_rewrite(self):
        self.report['bullet_bases'][0]['rewrite'] = 'Reduced pre-release defects with K6.'
        with patch('app.generate', return_value=self.report) as generate:
            result = self.client.post('/api/review', json=self.base)
        self.assertEqual(result.status_code, 200)
        self.assertNotIn('rewrite', result.json['report']['bullet_bases'][0])
        self.assertIn('K6 framework does not establish reduced pre-release defects', generate.call_args.args[0])
        self.assertIn('Add only a verified outcome', result.json['report']['improvements'][-1])

    def test_cv_advice_removes_speculative_percentages_and_known_status_questions(self):
        cv = self.cv + '\nCurrently pursuing an AI engineering bootcamp (in progress).'
        self.report['improvements'] = ['Reduce performance regressions by X%.', 'Clarify whether the bootcamp is ongoing.']
        self.report['next_steps'] = ['Show that K6 reduced regressions by [X]%.']
        with patch('app.generate', return_value=self.report):
            result = self.client.post('/api/review', json={**self.base, 'cv': cv})
        self.assertEqual(result.status_code, 200)
        advice = ' '.join(result.json['report']['improvements'] + result.json['report']['next_steps'])
        self.assertNotIn('X%', advice)
        self.assertNotIn('[X]%', advice)
        self.assertNotIn('Clarify whether', advice)
        self.assertNotIn('bootcamp', advice)
        self.assertIn('bootcamp is already clearly marked as in progress', ' '.join(result.json['report']['strengths']))
        self.assertIn('What outcome, if any', advice)

    def test_bootcamp_profile_does_not_repeat_dangling_sentence(self):
        self.report['improvements'] = ['Clarify whether the bootcamp is ongoing.']
        self.report['next_steps'] = ['Confirm bootcamp completion status.']
        cv = self.cv + '\nCurrently pursuing an AI engineering bootcamp. Combines'
        with patch('app.generate', return_value=self.report):
            result = self.client.post('/api/review', json={**self.base, 'cv': cv})
        self.assertEqual(result.status_code, 200)
        self.assertNotIn('Combines', str(result.json))

    def test_bootcamp_status_is_not_repeated_or_contradicted_across_report(self):
        cv = self.cv + '\nCurrently pursuing an AI engineering bootcamp.'
        self.report['summary'] = 'Strong QA experience. Clarify the status of the ongoing bootcamp.'
        self.report['score_explanation'] = 'Good role alignment. The bootcamp completion status is unclear.'
        for key in ('strengths', 'improvements', 'next_steps'):
            self.report[key] = ['Keep the bootcamp marked as in progress, as already stated in your CV.', 'Explain your verified project outcome.']
        with patch('app.generate', return_value=self.report):
            response = self.client.post('/api/review', json={**self.base, 'cv': cv})
        self.assertEqual(response.status_code, 200)
        report = response.json['report']
        self.assertEqual(report['summary'], 'Strong QA experience.')
        self.assertEqual(report['score_explanation'], 'Good role alignment.')
        combined = report['strengths'] + report['improvements'] + report['next_steps']
        self.assertEqual(sum('bootcamp' in item for item in combined), 1)
        self.assertEqual(combined.count('Explain your verified project outcome.'), 1)

    def test_generated_maintenance_rewrite_is_removed_but_exact_cv_base_is_kept(self):
        cv = self.cv + '\nBuilt a Playwright test automation framework.'
        self.report['bullet_bases'] = [{'source_quote': 'Built a Playwright test automation framework.', 'evidence_question': 'What result, if any, did you measure?'}]
        self.report['strengths'] = ['Your Playwright experience is relevant.', 'You developed and maintained a Playwright framework.']
        self.report['improvements'] = ['Replace the bullet with "Developed and maintained a Playwright framework."']
        self.report['next_steps'] = ['Developed and maintained a Playwright framework.']
        self.report['summary'] = 'Strong QA experience. Example: "Developed and maintained a Playwright framework."'
        self.report['rewrite'] = 'Developed and maintained a Playwright framework.'
        with patch('app.generate', return_value=self.report):
            response = self.client.post('/api/review', json={**self.base, 'cv': cv})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('maintained', str(response.json['report']).lower())
        self.assertNotIn('rewrite', response.json['report'])
        self.assertEqual(response.json['report']['bullet_bases'][0]['source_quote'], 'Built a Playwright test automation framework.')
        self.assertIn('Built a Playwright test automation framework.', str(response.json['report']['improvements']))

    def test_real_maintenance_evidence_is_not_removed(self):
        cv = self.cv + '\nDeveloped and maintained a Playwright framework.'
        self.report['strengths'] = ['"Developed and maintained a Playwright framework."']
        with patch('app.generate', return_value=self.report):
            response = self.client.post('/api/review', json={**self.base, 'cv': cv})
        self.assertEqual(response.status_code, 200)
        self.assertIn('maintained', str(response.json['report']['strengths']))
