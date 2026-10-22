import os
import unittest
from unittest.mock import patch
import app as module


class CoachingTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'OPENAI_API_KEY': '', 'APP_PASSWORD': ''})
        self.env.start()
        module.limits.clear()
        self.client = module.app.test_client()
        self.source = 'Our releases were slow. I owned the build process. I automated tests. Releases fell from 2 hours to 20 minutes.'

    def tearDown(self):
        self.env.stop()

    def test_demo_and_live_are_explicit(self):
        data = dict(source=self.source, skill='Automation')
        demo = self.client.post('/api/evidence', json={**data, 'demo': True})
        self.assertTrue(demo.json['demo'])
        self.assertEqual(demo.json['story']['situation'], self.source)
        self.assertEqual(self.client.post('/api/evidence', json=data).status_code, 400)

    def test_grounded_story_and_reject_invented_metric(self):
        data = dict(source=self.source, skill='Automation')
        story = dict(situation='Our releases were slow.', task='I owned the build process.', action='I automated tests.', result='')
        with patch('app.generate', return_value={'story': story}):
            result = self.client.post('/api/evidence', json=data)
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json['missing'], ['Result'])
            self.assertFalse(result.json['demo'])
        with patch('app.generate', return_value={'story': {**story, 'result': 'Saved $100,000.'}}):
            result = self.client.post('/api/evidence', json=data)
            self.assertEqual(result.status_code, 200)
            self.assertTrue(result.json['fallback'])
            self.assertEqual(result.json['story']['situation'], 'Our releases were slow.')
            self.assertEqual(result.json['story']['task'], 'I owned the build process.')
            self.assertEqual(result.json['story']['action'], 'I automated tests.')
            self.assertEqual(result.json['story']['result'], '')
            self.assertNotIn('$100,000', str(result.json))
            self.assertIn('extractive fallback', result.json['recovery_notice'])

    def test_adaptive_context_and_validation(self):
        base = dict(role='Engineer', focus='Explain personal contribution', goal='Move into leadership', total=3)
        with patch('app.generate', return_value={'question': 'Describe your contribution to a project.'}) as generate:
            self.assertEqual(self.client.post('/api/interview', json=base).status_code, 200)
            context = generate.call_args.args[1]
            self.assertEqual(context['practice_focus'], base['focus'])
            self.assertEqual(context['career_goal'], base['goal'])
            self.assertIn('coaching_task', context)
        result = self.client.post('/api/interview', json={**base, 'demo': True})
        self.assertIn(base['focus'], result.json['question'])
        self.assertEqual(self.client.post('/api/interview', json={**base, 'focus': 'x' * 1201}).status_code, 400)
        self.assertEqual(self.client.post('/api/evidence', json={'skill': 'x', 'source': []}).status_code, 400)

    def test_fallback_extracts_actions_without_copying_instructions_or_metrics(self):
        source='Our releases were unreliable. I owned the test suite. I built Playwright tests. Do not invent metrics. I have no measured results.'
        with patch('app.generate',return_value={'story':{'situation':source,'task':'','action':'','result':''}}):
            response=self.client.post('/api/evidence',json={'source':source,'skill':'Automation'})
        self.assertTrue(response.json['fallback'])
        self.assertEqual(response.json['story']['action'],'I built Playwright tests.')
        self.assertEqual(response.json['story']['task'],'I owned the test suite.')
        self.assertEqual(response.json['story']['result'],'')
        self.assertNotIn('invent metrics',str(response.json['story']))


if __name__ == '__main__':
    unittest.main()
