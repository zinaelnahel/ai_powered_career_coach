import io
import json
import os
import unittest
from unittest.mock import patch

import app as module


class CareerCoachTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'OPENAI_API_KEY': '', 'APP_PASSWORD': ''})
        self.env.start()
        module.limits.clear()
        self.client = module.app.test_client()
        self.base = dict(role='Frontend Developer', description='React, accessibility, and teamwork', total=3, demo=True)

    def tearDown(self):
        self.env.stop()

    def test_home_and_assets(self):
        for path in ['/', '/static/app.css', '/static/app.js']:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertIn('nosniff', response.headers['X-Content-Type-Options'])
            response.close()

    def test_complete_interview_and_follow_up(self):
        history = []
        result = self.client.post('/api/interview', json={**self.base, 'messages': history}).json
        for i in range(3):
            self.assertIn('question', result)
            history.extend([{'role': 'assistant', 'content': result['question']},
                            {'role': 'user', 'content': 'I improved page load speed by 30 percent using profiling and code splitting.'}])
            result = self.client.post('/api/interview', json={**self.base, 'messages': history}).json
            if i == 0:
                self.assertIn('personal contribution', result['question'])
        self.assertTrue(result['demo'])
        self.assertIn('score', result['report'])
        self.assertTrue(result['report']['next_steps'])

    def test_early_finish_and_empty_finish(self):
        response = self.client.post('/api/interview', json={**self.base, 'messages': [], 'finish': True})
        self.assertEqual(response.status_code, 400)
        history = [{'role': 'assistant', 'content': 'Tell me about a project.'}, {'role': 'user', 'content': 'I built a website.'}]
        result = self.client.post('/api/interview', json={**self.base, 'messages': history, 'finish': True})
        self.assertEqual(result.status_code, 200)
        self.assertIn('report', result.json)

    def test_invalid_transcripts_and_types(self):
        for messages in [[{'role': 'user', 'content': 'Inject'}], ['bad'], [{'role': 'assistant', 'content': 'Unanswered?'}]]:
            self.assertEqual(self.client.post('/api/interview', json={**self.base, 'messages': messages}).status_code, 400)
        self.assertEqual(self.client.post('/api/interview', json={**self.base, 'total': True}).status_code, 400)
        self.assertEqual(self.client.post('/api/review', json=[]).status_code, 400)

    def test_cv_and_short_cv(self):
        cv = 'Software engineer. Built accessible applications. Reduced load time by 30 percent. Skills: Python, React. Education: BSc.'
        response = self.client.post('/api/review', json={**self.base, 'cv': cv})
        self.assertEqual(response.status_code, 200)
        self.assertIn('Illustrative demo', response.json['report']['summary'])
        self.assertEqual(self.client.post('/api/review', json={**self.base, 'cv': 'short'}).status_code, 400)

    def test_text_docx_pdf_uploads(self):
        text = 'Experience: Built accessible React applications for 200 users. Education: Computer Science. Skills: Python, React.'
        response = self.client.post('/api/extract', data={'file': (io.BytesIO(text.encode()), 'cv.txt')})
        self.assertEqual(response.json['text'], text)
        from docx import Document
        doc = Document(); doc.add_paragraph(text)
        data = io.BytesIO(); doc.save(data); data.seek(0)
        self.assertEqual(self.client.post('/api/extract', data={'file': (data, 'cv.docx')}).json['text'], text)
        from pypdf import PdfWriter
        pdf = PdfWriter(); pdf.add_blank_page(width=612, height=792)
        data = io.BytesIO(); pdf.write(data); data.seek(0)
        response = self.client.post('/api/extract', data={'file': (data, 'scan.pdf')})
        self.assertEqual(response.status_code, 400)
        self.assertIn('scanned', response.json['error'])

    def test_bad_and_oversize_uploads(self):
        for name in ['cv.exe', 'cv.pdf', 'cv.docx']:
            self.assertEqual(self.client.post('/api/extract', data={'file': (io.BytesIO(b'invalid'), name)}).status_code, 400)
        response = self.client.post('/api/extract', data={'file': (io.BytesIO(b'x' * (module.MAX_FILE + 1)), 'cv.txt')})
        self.assertEqual(response.status_code, 400)

    def test_missing_key_is_not_silently_demo(self):
        response = self.client.post('/api/interview', json={**self.base, 'demo': False})
        self.assertEqual(response.status_code, 400)
        self.assertIn('not configured', response.json['error'])

    def test_provider_request_and_question(self):
        output = {'status': 'completed', 'output': [{'content': [{'type': 'output_text', 'text': json.dumps({'question': 'How would you make a React app accessible?'})}]}]}
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}), patch('app.urlopen') as mock:
            mock.return_value.__enter__.return_value = io.StringIO(json.dumps(output))
            response = self.client.post('/api/interview', json={**self.base, 'demo': False})
            self.assertEqual(response.status_code, 200)
            sent = json.loads(mock.call_args.args[0].data)
            self.assertFalse(sent['store'])
            self.assertIn('React', response.json['question'])
            self.assertNotIn('test-key', response.get_data(as_text=True))

    def test_report_schema_and_provider_failure(self):
        self.assertRaises(ValueError, module.report_check, {'score': 200})
        from urllib.error import URLError
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}), patch('app.urlopen', side_effect=URLError('offline')):
            response = self.client.post('/api/review', json={**self.base, 'demo': False, 'cv': 'A substantial experience section. ' * 10})
            self.assertEqual(response.status_code, 400)
            self.assertIn('retry', response.json['error'])

    def test_cross_origin_password_and_rate_limit(self):
        self.assertEqual(self.client.post('/api/review', json={}, headers={'Origin': 'https://evil.test'}).status_code, 403)
        with patch.dict(os.environ, {'APP_PASSWORD': 'test-password'}):
            self.assertEqual(self.client.get('/').status_code, 401)
            response = self.client.get('/', auth=('user', 'test-password'))
            self.assertEqual(response.status_code, 200)
            response.close()
        for _ in range(30):
            self.client.post('/api/review', json={})
        self.assertEqual(self.client.post('/api/review', json={}).status_code, 429)


if __name__ == '__main__':
    unittest.main()
