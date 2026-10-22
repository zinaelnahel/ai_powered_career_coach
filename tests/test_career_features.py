import io
import json
import os
import unittest
from unittest.mock import patch

import app as module
from career_features import cv_evidence_excerpt


class CareerLabTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'OPENAI_API_KEY': '', 'APP_PASSWORD': ''})
        self.env.start()
        self.links = patch('career_features.check_job_links', side_effect=lambda jobs: [{**job, 'link_status': 'unconfirmed'} for job in jobs])
        self.linkmock = self.links.start()
        self.addCleanup(self.links.stop)
        module.limits.clear()
        self.client = module.app.test_client()
        self.cv = 'Frontend developer. Built accessible React applications with JavaScript for 200 users. Education: Computer Science. Skills: React, JavaScript, HTML, CSS, accessibility.'
        self.description = 'We need React, Python, SQL, communication and accessibility skills to build customer-facing applications.'
        self.base = dict(role='Frontend Developer', cv=self.cv, description=self.description, demo=True)

    def tearDown(self):
        self.env.stop()

    def response(self, value, sources=None):
        output = [{'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps(value), 'annotations': []}]}]
        if sources is not None:
            output.insert(0, {'type': 'web_search_call', 'action': {'sources': sources}})
        return io.StringIO(json.dumps({'status': 'completed', 'output': output}))

    def live(self, endpoint, value, data=None, sources=None):
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-only'}), patch('app.urlopen') as mock:
            mock.return_value.__enter__.return_value = self.response(value, sources)
            response = self.client.post(endpoint, json={**self.base, 'demo': False, **(data or {})})
            payload = json.loads(mock.call_args.args[0].data)
        return response, payload

    def test_job_demo_is_fictional_and_not_applicable(self):
        response = self.client.post('/api/jobs', json={**self.base, 'location': 'Berlin'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json['demo'])
        self.assertIsNone(response.json['jobs'][0]['url'])
        self.assertIn('fictional', response.json['jobs'][0]['company'])

    def test_search_keeps_candidates_beyond_old_eight_limit(self):
        jobs=[{'title':'Senior QA Engineer','company':f'Employer {i}','location':'Valencia, Spain',
               'description':'QA automation.','url':f'https://employer{i}.test/jobs/qa'} for i in range(16)]
        self.linkmock.side_effect=lambda jobs: [{**job,'location_verified':True} for job in jobs]
        response,payload=self.live('/api/jobs',{'jobs':jobs},{'role':'Senior QA Engineer','location':'Spain'},[{'url':job['url']} for job in jobs])
        self.assertEqual(response.status_code,200)
        self.assertEqual(len(response.json['jobs']),16)
        self.assertEqual(response.json['search_diagnostics']['researched'],16)
        self.assertIn('test automation engineer',payload['input'])
        self.assertEqual(payload['max_output_tokens'],6500)

    def test_search_recovers_retrieved_dkb_posting_omitted_from_shortlist(self):
        from pathlib import Path
        from job_links import check_job_links
        link='https://job-boards.greenhouse.io/dkbcodefactory/jobs/8004226003'
        html=(Path(__file__).parent/'fixtures'/'dkb_valencia.html').read_bytes()
        self.linkmock.side_effect=check_job_links
        with patch('job_links.fetch_page',return_value=(200,None,'text/html',html)):
            response,_=self.live('/api/jobs',{'jobs':[]},{'role':'Senior QA Engineer','location':'Spain'},[{'url':link}])
        self.assertEqual(response.status_code,200)
        self.assertEqual(len(response.json['jobs']),1)
        self.assertEqual(response.json['jobs'][0]['title'],'Senior QA Automation Engineer')
        self.assertEqual(response.json['jobs'][0]['location'],'Valencia, Spain')
        self.assertNotIn('_discover_role',response.json['jobs'][0])
        self.assertEqual(response.json['search_diagnostics']['source_discovered'],1)

    def test_company_policy_is_not_assumed_to_apply_to_subsidiary_country(self):
        link='https://www.dkb.de/karriere/berufserfahrene/tech'
        brief={'overview':'DKB context','values':[{'value':'Work abroad','evidence':'Up to 30 days in the EU','source_url':link}],'topics':[],'questions':[]}
        with patch('company_facts.verified_company',return_value=([], 'Identity unavailable.')):
            response,_=self.live('/api/company-prep',brief,{'company':'DKB Code Factory, Spain'},[{'url':link}])
        value=response.json['brief']['values'][0]
        self.assertIn('parent-company context',value['basis'])
        self.assertIn('Spain',value['applicability'])
        self.assertIn('not been independently established',value['applicability'])

    def test_company_generated_button_label_is_rejected(self):
        link='https://example.test/culture'
        brief={'overview':'Company overview.','values':[{'value':'Learn more','evidence':'Learn more about our people','source_url':link},{'value':'People first','evidence':'We invest in our people.','source_url':link}],'topics':[]}
        with patch('company_facts.verified_company',return_value=([],'Identity unavailable.')):
            response,_=self.live('/api/company-prep',brief,{'company':'Example'},[{'url':link}])
        self.assertEqual([item['value'] for item in response.json['brief']['values']],['People first'])

    def test_live_jobs_require_retrieved_urls_and_exclude_cv_from_search(self):
        job = {'title': 'Frontend Developer', 'company': 'Example', 'location': 'Berlin', 'description': self.description, 'url': 'https://example.com/jobs/42'}
        result = {'summary': 'Found an advertised role. Availability must be checked.', 'jobs': [job, {**job, 'url': 'https://invented.test/fake'}]}
        self.linkmock.side_effect = lambda jobs: [{**job, 'location_verified': True} for job in jobs]
        response, payload = self.live('/api/jobs', result, {'location': 'Berlin'}, [{'url': job['url'], 'title': 'Example careers'}])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json['jobs']), 1)
        self.assertEqual(payload['tool_choice'], 'required')
        self.assertEqual(payload['tools'], [{'type': 'web_search'}])
        self.assertNotIn('cv', json.loads(payload['input'].split('\n')[-1]))
        self.assertNotIn(self.cv, payload['input'])
        self.assertFalse(payload['store'])

    def test_model_cannot_forge_search_source_metadata(self):
        response, _ = self.live('/api/jobs', {'summary': 'Invented', 'jobs': [], '_sources': [{'url': 'https://fake.test/job'}]}, sources=[])
        self.assertEqual(response.status_code, 400)
        self.assertIn('no usable sources', response.json['error'])

    def test_demo_fit_detects_evidence_and_missing_skills(self):
        response = self.client.post('/api/fit', json=self.base)
        self.assertEqual(response.status_code, 200)
        analysis = response.json['analysis']
        self.assertEqual({item['skill'] for item in analysis['matched_skills']}, {'react', 'accessibility'})
        self.assertEqual({item['skill'] for item in analysis['missing_skills']}, {'python', 'sql', 'communication'})
        self.assertEqual(analysis['score'], 40)
        for item in analysis['matched_skills']:
            self.assertIn(item['evidence'], self.cv)

    def test_live_fit_rejects_fabricated_cv_evidence(self):
        result = {'score': 80, 'summary': 'Good fit', 'matched_skills': [{'skill': 'React', 'evidence': 'Managed a team of 100 engineers'}], 'missing_skills': [], 'improvements': ['Add outcomes.']}
        response, _ = self.live('/api/fit', result)
        self.assertEqual(response.status_code, 400)
        result['matched_skills'][0]['evidence'] = 'Built accessible React applications'
        response, _ = self.live('/api/fit', result)
        self.assertEqual(response.status_code, 200)

    def test_fit_accepts_extraction_spacing_and_returns_original_evidence(self):
        cv = 'Frontend developer. Built accessible\n  React applications for 200 users. ' + self.cv
        result = {'score': 80, 'summary': 'Good fit', 'matched_skills': [{'skill': 'React', 'evidence': '"Built accessible React applications for 200 users."'}], 'missing_skills': [], 'improvements': ['Add outcomes.']}
        response, _ = self.live('/api/fit', result, {'cv': cv})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['analysis']['matched_skills'][0]['evidence'], 'Built accessible\n  React applications for 200 users.')

    def test_evidence_typography_preserves_original_and_rejects_changed_claims(self):
        cv = "Delivered client\u2019s work with cross\u2011functional teams and of\ufb01ce tools for 200 users."
        self.assertEqual(cv_evidence_excerpt(cv, "client's work with cross-functional teams"), "client\u2019s work with cross\u2011functional teams")
        self.assertEqual(cv_evidence_excerpt(cv, 'office tools'), 'of\ufb01ce tools')
        for quote in ('for 2000 users', 'Led cross-functional teams', 'Delivered office tools for 200 users', '   ', '\u00ad'):
            with self.subTest(quote=quote), self.assertRaises(ValueError):
                cv_evidence_excerpt(cv, quote)

    def test_jobs_summary_and_sources_follow_filtered_cards(self):
        result = {'summary': 'I found several QA positions.', 'jobs': [{'title': 'Senior QA Engineer', 'company': 'Example', 'location': 'Spain', 'description': 'QA automation role.', 'url': 'https://unverified.test/job'}]}
        response, _ = self.live('/api/jobs', result, {'location': 'Spain or remote EU'}, [{'url': 'https://research.test/sre', 'title': 'Unrelated SRE research'}])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['jobs'], [])
        self.assertEqual(response.json['sources'], [])
        self.assertIn('No source-backed job listings', response.json['summary'])
        self.assertNotIn('found several', response.json['summary'])
        link = 'https://employer.test/jobs/qa'
        result['jobs'][0]['url'] = link
        response, _ = self.live('/api/jobs', result, sources=[{'url': link, 'title': 'QA vacancy'}, {'url': 'https://research.test/sre', 'title': 'SRE vacancy'}])
        self.assertEqual(len(response.json['jobs']), 1)
        self.assertTrue(response.json['summary'].startswith('1 source-backed job listing returned'))
        self.assertEqual([source['url'] for source in response.json['sources']], [link])

    def test_roadmap_sequence_budget_and_personalization(self):
        response = self.client.post('/api/roadmap', json={**self.base, 'gaps': 'Python SQL', 'weeks': 3, 'hours': 1})
        self.assertEqual(response.status_code, 200)
        weeks = response.json['plan']['weeks']
        self.assertEqual([item['week'] for item in weeks], [1, 2, 3])
        self.assertEqual(weeks[0]['focus'], 'python')
        self.assertTrue(all(sum(a['hours'] for a in week['activities']) <= 1 for week in weeks))
        self.assertEqual(self.client.post('/api/roadmap', json={'role': 'Engineer', 'demo': True}).status_code, 400)
        self.assertEqual(self.client.post('/api/roadmap', json={**self.base, 'weeks': True}).status_code, 400)

    def test_live_roadmap_rejects_excess_hours(self):
        plan = {'summary': 'Plan based on CV.', 'weeks': [{'week': 1, 'focus': 'SQL', 'activities': [{'task': 'Practice joins', 'hours': 6}], 'deliverable': 'Query project', 'success_check': 'Correct joins', 'resource_hint': 'Official database tutorial'}]}
        response, _ = self.live('/api/roadmap', plan, {'weeks': 1, 'hours': 2})
        self.assertEqual(response.status_code, 400)
        plan['weeks'][0]['activities'][0]['hours'] = 2
        response, payload = self.live('/api/roadmap', plan, {'weeks': 1, 'hours': 2, 'feedback': 'Explain tradeoffs clearly.'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('Explain tradeoffs', payload['input'])
        self.assertIn('Do not repeat beginner training for evidenced skills', payload['instructions'])
        self.assertIn('official documentation chapter and exercise', payload['instructions'])

    def test_small_nonmobile_week_recovers_missing_optional_generated_details(self):
        plan={'summary':'One small resilience exercise.','weeks':[{'week':1,'focus':'Distributed systems timeouts'}]}
        response,_=self.live('/api/roadmap',plan,{'weeks':1,'hours':5})
        self.assertEqual(response.status_code,200)
        week=response.json['plan']['weeks'][0]
        self.assertIn('single-file dependency stub',week['activities'][0]['task'])
        self.assertIn('unexecuted',week['deliverable'])

    def test_company_demo_does_not_invent_company_values(self):
        response = self.client.post('/api/company-prep', json={**self.base, 'company': 'Acme'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['brief']['values'], [])
        self.assertEqual(response.json['sources'], [])
        self.assertIn('No company research', response.json['brief']['overview'])

    def test_company_live_filters_unsourced_facts(self):
        link = 'https://example.com/values'
        brief = {'overview': 'Company overview.', 'values': [{'value': 'Ownership', 'evidence': 'Official values page describes responsibility.', 'source_url': link}, {'value': 'Fake', 'evidence': 'Not sourced', 'source_url': 'javascript:alert(1)'}], 'topics': [{'topic': 'Ownership', 'reason': 'Practice a relevant example.', 'source_url': link}], 'questions': ['Tell me about a project you owned.']}
        response, payload = self.live('/api/company-prep', brief, {'company': 'Example'}, [{'url': link, 'title': 'Values'}])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json['brief']['values']), 1)
        self.assertEqual(len(response.json['sources']), 1)
        self.assertNotIn('cv', json.loads(payload['input'].split('\n')[-1]))

    def test_validation_and_live_key_required(self):
        for endpoint in ('jobs', 'fit', 'roadmap', 'company-prep'):
            self.assertEqual(self.client.post('/api/' + endpoint, json={}).status_code, 400)
            data = {**self.base, 'demo': False, 'company': 'Example', 'review': 'Review feedback that covers content and clarity.'}
            response = self.client.post('/api/' + endpoint, json=data)
            self.assertEqual(response.status_code, 400)
            self.assertIn('not configured', response.json['error'])

    def test_jobs_parse_wrapped_json_without_fabricating_sources(self):
        value = {'summary': 'No listings.', 'jobs': []}
        raw = {'status': 'completed', 'output': [
            {'type': 'web_search_call', 'action': {'sources': [{'url': 'https://example.com/careers'}]}},
            {'type': 'message', 'content': [{'type': 'output_text', 'text': 'Search results:\n' + json.dumps(value) + '\nSee sources.'}]}]}
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-only'}), patch('app.urlopen') as mock:
            mock.return_value.__enter__.return_value = io.StringIO(json.dumps(raw))
            response = self.client.post('/api/jobs', json={**self.base, 'demo': False})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['jobs'], [])
        self.assertEqual(mock.call_count, 1)

    def test_jobs_retry_malformed_output_once_and_preserve_location(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-only'}), patch('app.urlopen') as mock:
            bad = {'status': 'completed', 'output': [{'content': [{'type': 'output_text', 'text': '{broken'}]}]}
            mock.return_value.__enter__.side_effect = [io.StringIO(json.dumps(bad)), self.response({'jobs': []}, [{'url': 'https://example.com/careers'}])]
            response = self.client.post('/api/jobs', json={**self.base, 'demo': False, 'location': 'Spain or remote EU'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock.call_count, 2)
        payload = json.loads(mock.call_args.args[0].data)
        self.assertIn('search each alternative separately', payload['instructions'])
        self.assertEqual(json.loads(payload['input'].split('\n')[-1])['location'], 'Spain or remote EU')

    def test_jobs_retry_is_bounded(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-only'}), patch('app.urlopen') as mock:
            mock.return_value.__enter__.side_effect = lambda: io.StringIO(json.dumps({'status': 'completed', 'output': []}))
            response = self.client.post('/api/jobs', json={**self.base, 'demo': False})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(mock.call_count, 2)

    def test_job_tracking_tags_match_without_accepting_directories_or_duplicates(self):
        job = {'title': 'QA Engineer', 'company': 'Example', 'location': 'Berlin', 'description': 'Automated software testing.', 'url': 'https://example.com/jobs/42?job_id=42'}
        directory = {**job, 'url': 'https://www.xing.com/jobs/qa-engineer-jobs-in-berlin'}
        refs = [{'url': job['url'] + '&utm_source=openai'}, {'url': directory['url'] + '?utm_source=openai'}]
        response, _ = self.live('/api/jobs', {'jobs': [job, job, directory, {**job, 'url': 'https://example.com/jobs/42?job_id=43'}]}, sources=refs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json['jobs']), 1)
        self.assertEqual(response.json['sources'][0]['url'], job['url'])

    def test_company_prep_recovers_malformed_output_and_matches_tracking_tags(self):
        link = 'https://example.com/values'
        brief = {'overview': 'Example company overview.', 'values': [{'value': 'Ownership', 'evidence': 'Value on company page.', 'source_url': link}], 'topics': [], 'questions': ['Tell me about taking ownership.']}
        bad = {'status': 'completed', 'output': [{'content': [{'type': 'output_text', 'text': 'Not valid JSON.'}]}]}
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-only'}), patch('app.urlopen') as mock:
            mock.return_value.__enter__.side_effect = [io.StringIO(json.dumps(bad)), self.response(brief, [{'url': link + '?utm_source=openai'}])]
            response = self.client.post('/api/company-prep', json={**self.base, 'company': 'Example', 'demo': False})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock.call_count, 2)
        self.assertEqual(len(response.json['brief']['values']), 1)
        self.assertNotIn(self.cv, json.loads(mock.call_args.args[0].data)['input'])

    def test_stale_link_filter_updates_cards_summary_and_sources(self):
        job = {'title': 'QA Engineer', 'company': 'Example', 'location': 'Berlin', 'description': 'QA automation.', 'url': 'https://employer.test/jobs/42'}
        self.linkmock.side_effect = lambda jobs: []
        response, _ = self.live('/api/jobs', {'jobs': [job]}, sources=[{'url': job['url']}])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['jobs'], [])
        self.assertEqual(response.json['sources'], [])
        self.assertIn('No source-backed', response.json['summary'])

    def test_roadmap_links_are_curated_not_model_urls(self):
        plan = {'summary': 'Plan based on CV.', 'weeks': [{'week': 1, 'focus': 'LLM evaluation with pytest', 'activities': [{'task': 'Build a small evaluation harness.', 'hours': 2}], 'deliverable': 'Evaluation harness', 'success_check': 'Run checks', 'resource_hint': 'Hugging Face evaluation overview and pytest fixtures.', 'resource_links': [{'url': 'https://invented.test/course'}]}]}
        response, _ = self.live('/api/roadmap', plan, {'weeks': 1, 'hours': 2})
        self.assertEqual(response.status_code, 200)
        links = response.json['plan']['weeks'][0]['resource_links']
        self.assertEqual({link['url'] for link in links}, {'https://docs.pytest.org/en/stable/how-to/fixtures.html'})


    def test_specific_resources_follow_named_documentation(self):
        from career_features import learning_resources, job_detail_url
        for hint, expected in [('GitLab CI/CD pipeline', 'docs.gitlab.com'), ('Lighteval quick tour', '/lighteval/'), ('Creating a custom metric', '/creating_and_sharing'), ('Choosing metrics for precision and recall', '/choosing_a_metric'), ('Evaluation suite', '/evaluation_suite'), ('Bias and fairness considerations', '/considerations')]:
            links = learning_resources({'focus': 'LLM evaluation', 'resource_hint': hint})
            self.assertIn(expected, links[0]['url'])
        self.assertFalse(job_detail_url('https://es.indeed.com/jobs?q=Q-tech'))
        self.assertTrue(job_detail_url('https://es.indeed.com/viewjob?jk=abc123'))

    def test_location_filter_updates_jobs_count_and_sources(self):
        good = dict(title='Senior QA Engineer', company='Spain employer', location='Spain',
                    description='QA automation', url='https://employer.test/jobs/spain')
        bad = {**good, 'company': 'Kiefer', 'location': 'Hybrid, Athens', 'url': 'https://employer.test/jobs/athens'}
        remote = {**good, 'location': 'Remote', 'url': 'https://employer.test/jobs/remote'}
        self.linkmock.side_effect = lambda jobs: [{**job, 'location_verified': job['url'] == good['url']} for job in jobs]
        response, payload = self.live('/api/jobs', {'jobs': [good, bad, remote]}, {'location': 'Spain'}, [{'url': job['url']} for job in (good, bad, remote)])
        self.assertEqual(response.status_code, 200)
        self.assertEqual([job['url'] for job in response.json['jobs']], [good['url']])
        self.assertTrue(response.json['summary'].startswith('1 source-backed'))
        self.assertEqual([source['url'] for source in response.json['sources']], [good['url']])
        self.assertNotIn('_requested_location', response.json['jobs'][0])
        self.assertIn('Hybrid Athens is ineligible', payload['instructions'])
        self.linkmock.side_effect = lambda jobs: jobs
        response, _ = self.live('/api/jobs', {'jobs': [remote]}, {'location': 'Spain'}, [{'url': remote['url']}])
        self.assertEqual(response.json['jobs'], [])
        self.assertEqual(response.json['sources'], [])

    def test_real_source_validation_rejects_athens_and_remote_without_country(self):
        self.links.stop()
        jobs = [dict(title='Senior QA Engineer', company=name, location=place,
                     description='QA automation', url='https://employer.test/jobs/' + name,
                     location_evidence=evidence)
                for name, place, evidence in [
                    ('kiefer', 'Hybrid, Athens', {'quote': 'Hybrid, Athens', 'place': 'Athens', 'mode': 'hybrid'}),
                    ('unknown', 'Remote', {'quote': 'Remote', 'place': 'Spain', 'mode': 'remote'}),
                    ('spanish', 'Spain', {'quote': 'Remote from Spain', 'place': 'Spain', 'mode': 'remote'}),
                    ('forged', 'Spain', {'quote': 'Remote from Spain', 'place': 'Spain', 'mode': 'remote'})]]
        pages = {'kiefer': 'Hybrid, Athens', 'unknown': 'Remote', 'spanish': 'Remote from Spain', 'forged': 'Hybrid, Athens'}
        def fetch(link, deadline):
            html = '<h1>Senior QA Engineer</h1><p>' + pages[link.rsplit('/', 1)[-1]] + '</p><button>Apply</button>'
            return 200, None, 'text/html', html.encode()
        with patch('job_links.fetch_page', side_effect=fetch):
            response, _ = self.live('/api/jobs', {'jobs': jobs}, {'location': 'Spain'}, [{'url': job['url']} for job in jobs])
        self.assertEqual(response.status_code, 200)
        self.assertEqual([job['company'] for job in response.json['jobs']], ['spanish'])
        self.assertEqual(response.json['jobs'][0]['location_evidence']['quote'], 'Remote from Spain')
        self.assertEqual(response.json['jobs'][0]['location'], 'Spain (remote)')
        self.assertEqual(len(response.json['sources']), 1)

    def test_llm_objective_wins_over_incidental_playwright_hint(self):
        from career_features import learning_resources
        robust = learning_resources({'focus': 'LLM robustness and prompt injection tests', 'resource_hint': 'Playwright introduction', 'activities': []})
        self.assertIn('garak', robust[0]['url'])
        baseline = learning_resources({'focus': 'LLM evaluation baseline', 'resource_hint': 'Create a dataset and benchmark', 'activities': []})
        self.assertIn('adding-a-custom-task', baseline[0]['url'])

    def test_dkb_search_fixture_passes_entire_source_and_location_pipeline(self):
        from pathlib import Path
        self.links.stop()
        link = 'https://job-boards.greenhouse.io/dkbcodefactory/jobs/8004226003'
        job = dict(title='Senior QA Automation Engineer', company='DKB Code Factory', location='Valencia, Spain', description='QA automation role.', url=link)
        html = (Path(__file__).parent / 'fixtures' / 'dkb_valencia.html').read_bytes()
        for role, location in [('Senior QA Engineer', 'Spain'), ('Senior QA Automation Engineer', 'Valencia')]:
            with patch('job_links.fetch_page', return_value=(200, None, 'text/html', html)):
                response, _ = self.live('/api/jobs', {'jobs': [job]}, {'role': role, 'location': location}, [{'url': link}])
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['jobs'][0]['url'], link)
            self.assertEqual(response.json['search_diagnostics']['researched'], 1)
            self.assertEqual(response.json['search_diagnostics']['shown'], 1)

    def test_same_application_target_is_one_card_prefer_direct_employer(self):
        direct = 'https://job-boards.greenhouse.io/dkbcodefactory/jobs/8004226003'
        mirror = 'https://jobseek.test/jobs/dkb-qa'
        other = direct.replace('8004226003', '8004226004')
        jobs = [dict(title='Senior QA Automation Engineer', company='DKB Code Factory', location='Valencia, Spain', description='QA role.', url=link) for link in (mirror, direct, other)]
        self.linkmock.side_effect = lambda items: [{**job, 'location_verified': True, 'application_url': direct + '?ref=jobseek.dev' if job['url'] == mirror else job['url']} for job in items]
        response, _ = self.live('/api/jobs', {'jobs': jobs}, {'location': 'Valencia'}, [{'url': job['url']} for job in jobs])
        self.assertEqual(response.status_code, 200)
        self.assertEqual([job['url'] for job in response.json['jobs']], [direct, other])
        self.assertEqual(response.json['search_diagnostics']['duplicates_removed'], 1)
        self.assertEqual(response.json['search_diagnostics']['shown'], 2)
        self.assertEqual([item['url'] for item in response.json['sources']], [direct, other])

    def test_cicd_week_does_not_reuse_the_robustness_intro(self):
        from career_features import learning_resources
        for hint, expected in [('Run garak LLM robustness checks in GitLab CI', 'docs.gitlab.com/ci/'), ('Run garak LLM robustness checks in GitHub Actions', 'docs.github.com/en/actions/')]:
            week = dict(focus='CI/CD integration for LLM evaluations', resource_hint=hint,
                        activities=[{'task': 'Run the robustness suite on every commit.'}])
            resources = learning_resources(week)
            self.assertIn(expected, resources[0]['url'])
            self.assertNotIn('garak', resources[0]['url'])


if __name__ == '__main__':
    unittest.main()
