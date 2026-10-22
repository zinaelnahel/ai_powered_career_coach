import unittest
import os
from unittest.mock import patch
from content_quality import grounded_interview, coherent_fit
from learning_scope import scope_small_week
from career_features import learning_resources
from company_facts import culture_values


class LatestAuditTests(unittest.TestCase):
    def test_live_interview_route_returns_guarded_feedback(self):
        import app as module
        module.limits.clear()
        wrong='Mentoring experience with pairing method and feedback collection.'
        report={'score':60,'summary':'A practice report.','score_explanation':'Subjective assessment.','strengths':[wrong],'improvements':['Explain personal contribution.'],'next_steps':['Provide a real example.']}
        history=[{'role':'assistant','content':'How would you mentor a teammate?'},{'role':'user','content':'A technique I would use is pairing on one real test case and collecting feedback. These details are proposed.'}]
        with patch.dict(os.environ,{'APP_PASSWORD':''}),patch('app.generate',return_value=report):
            response=module.app.test_client().post('/api/interview',json={'role':'QA Engineer','messages':history,'total':3,'finish':True})
        self.assertEqual(response.status_code,200)
        self.assertNotIn(wrong,str(response.json['report']))
        self.assertTrue(response.json['report']['proposal_evidence'])

    def test_proposal_is_not_credited_as_experience_in_any_report_section(self):
        answer='I have coaching experience. A technique I would use is pairing on one real test case and collecting feedback. These details are proposed, not recorded past actions.'
        wrong='Mentoring experience with pairing method and feedback collection.'
        report={'score':60,'summary':wrong,'score_explanation':wrong,'strengths':[wrong],'improvements':[wrong],'next_steps':[wrong]}
        result=grounded_interview(report,[{'role':'user','content':answer}])
        for key in ('summary','score_explanation','strengths','improvements','next_steps'):
            self.assertNotIn(wrong,str(result[key]))
        self.assertIn('proposed',result['proposal_evidence'][0]['status'])
        self.assertIn(result['proposal_evidence'][0]['source_quote'],answer)
        self.assertTrue(any('not credited as past experience' in item for item in result['strengths']))

    def test_no_hypothetical_guard_for_real_past_answer(self):
        report={'strengths':['Implemented pairing in a recorded coaching session.']}
        self.assertEqual(grounded_interview(report.copy(),[{'role':'user','content':'I implemented pairing in a coaching session.'}]),report)

    def test_mixed_answer_preserves_playwright_and_qualifies_only_wiremock(self):
        for separator in ('. ', '; ', ', but ', ' and '):
            answer='I built Playwright tests for our release pipeline'+separator+'I would use WireMock in a future project.'
            real='Demonstrated experience building Playwright tests for the release pipeline.'
            proposed='Demonstrated experience using WireMock in a project.'
            report={'score':70,'summary':real+' '+proposed,'score_explanation':real,
                    'strengths':[real,proposed],'improvements':['Explain measurable outcomes.'],'next_steps':['Practise one example.']}
            with self.subTest(separator=separator):
                result=grounded_interview(report,[{'role':'user','content':answer}])
                self.assertIn(real,result['summary'])
                self.assertIn(real,result['strengths'])
                self.assertEqual(result['score_explanation'],real)
                self.assertNotIn(proposed,str(result))
                self.assertTrue(all('Playwright' not in item['source_quote'] for item in result['proposal_evidence']))
                self.assertTrue(any('WireMock' in item['source_quote'] for item in result['proposal_evidence']))

    def test_partial_backend_performance_evidence_is_carried_to_gaps(self):
        cv='Built a K6 framework for frontend applications and backend services for performance benchmarking.'
        report={'score':70,'summary':'No backend experience.','matched_skills':[], 'missing_skills':[{'skill':'Backend/API test automation','reason':'No explicit backend evidence','priority':'high'},{'skill':'Java/Kotlin','reason':'Not evidenced','priority':'high'}],'improvements':[]}
        result=coherent_fit(report,cv)
        self.assertEqual(result['matched_skills'][0]['evidence'],cv)
        self.assertIn('Partial coverage',result['validated_gaps'][0]['reason'])
        self.assertEqual(result['validated_gaps'][0]['partial_evidence'],cv)
        self.assertEqual(result['missing_skills'][1]['skill'],'Java/Kotlin')
        self.assertIn('not recalculated',result['score_consistency'])

    def test_k6_only_match_is_narrowed_instead_of_satisfying_functional_api(self):
        quote='Built a K6 framework for frontend applications and backend services for performance benchmarking.'
        for skill,evidence in [('Backend/API test automation',quote),('API functional and performance testing',quote),('API testing','Built a K6 framework')]:
            with self.subTest(skill=skill,evidence=evidence):
                report={'score':82,'summary':'API automation is matched.','matched_skills':[{'skill':skill,'evidence':evidence}], 'missing_skills':[], 'improvements':[]}
                result=coherent_fit(report,quote)
                self.assertEqual(result['matched_skills'][0]['skill'],'Backend performance testing (partial coverage)')
                self.assertEqual(result['validated_gaps'][0]['skill'],skill)
                self.assertIn('Partial coverage',result['validated_gaps'][0]['reason'])

    def test_functional_api_evidence_is_not_downgraded_with_k6(self):
        quote='Built K6 performance tests and REST Assured functional API tests.'
        report={'score':82,'summary':'API evidence.','matched_skills':[{'skill':'API testing','evidence':quote}], 'missing_skills':[], 'improvements':[]}
        self.assertEqual(coherent_fit(report,quote)['matched_skills'][0]['skill'],'API testing')

    def test_scope_and_resources_preserve_specific_objectives(self):
        for focus,task,link in [('Backend API test automation with Java and REST Assured','HTTP GET','rest-assured'),('Mocking and service virtualization in Java','stub response','wiremock'),('Distributed-systems resilience in Java','timeout/retry','sre.google'),('Java foundations','one function','dev.java')]:
            with self.subTest(focus=focus):
                week={'focus':focus,'resource_hint':'Java classes and objects'}
                scope_small_week(week,5)
                self.assertIn(task,week['activities'][1]['task'])
                self.assertIn(link,learning_resources(week)[0]['url'])
                self.assertEqual(sum(item['hours'] for item in week['activities']),5)
                self.assertIn('unexecuted',week['deliverable'])

    def test_culture_values_use_exact_first_party_statements(self):
        refs={'https://www.examplelabs.test/imprint':{'url':'https://www.examplelabs.test/imprint'}}
        body=b'<h1>Culture</h1><h2>Our values</h2><h3>People come first</h3><p>We learn through experimentation.</p><p>We take responsibility for our customers.</p>'
        with patch('company_facts.fetch_page',return_value=(200,None,'text/html',body)):
            values,checks=culture_values('Example Labs',refs)
        self.assertTrue(values)
        self.assertTrue(all(item['evidence'].encode() in body for item in values))
        self.assertEqual(checks[0]['url'],'https://www.examplelabs.test/culture')

    def test_culture_blocking_is_disclosed_without_parent_fallback(self):
        refs={'https://www.examplelabs.test/imprint':{}}
        with patch('company_facts.fetch_page',return_value=(503,None,'text/html',b'Blocked')):
            values,checks=culture_values('Example Labs',refs)
        self.assertEqual(values,[])
        self.assertIn('HTTP 503',checks[0]['status'])

    def test_culture_buttons_are_not_values(self):
        refs={'https://www.examplelabs.test/imprint':{}}
        body=b'<h2>Our values</h2><a href="/people">Learn more</a><button>Learn more about customers</button><h3>People come first</h3><p>We learn through experimentation.</p>'
        with patch('company_facts.fetch_page',return_value=(200,None,'text/html',body)):
            values,_=culture_values('Example Labs',refs)
        self.assertTrue(values)
        self.assertFalse(any(item['value'].startswith('Learn more') for item in values))
