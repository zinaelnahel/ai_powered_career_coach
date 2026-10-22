import os
from datetime import date
import unittest
from unittest.mock import patch
import app as module
from company_facts import verified_company
from content_quality import plain_prose, english_evidence, coherent_fit
from career_features import learning_resources


class AuditQualityTests(unittest.TestCase):
    def test_wrong_dkb_parent_is_replaced_from_official_imprint(self):
        link = 'https://www.dkbcodefactory.com/imprint'
        page = b'<h1>Imprint</h1><p>DKB Code Factory GmbH</p><p>A company of Deutsche Kreditbank AG</p>'
        wrong = {'identity_facts':[{'kind':'parent','value':'Deutsche Bank','source_quote':'A company of Deutsche Kreditbank AG','source_url':link}]}
        with patch('company_facts.fetch_page', return_value=(200,None,'text/html',page)):
            facts, overview = verified_company(wrong, 'DKB Code Factory, Germany and Spain', {link:{'url':link}})
        self.assertEqual(facts[0]['value'], 'Deutsche Kreditbank AG')
        self.assertNotIn('Deutsche Bank', overview)
        self.assertIn('Deutsche Kreditbank AG', overview)

    def test_other_abbreviation_uses_its_own_source_not_dkb_rule(self):
        link = 'https://abc.example/imprint'
        page = b'<h1>ABC Labs</h1><p>A company of Example Holdings Ltd</p>'
        with patch('company_facts.fetch_page', return_value=(200,None,'text/html',page)):
            facts, overview = verified_company({}, 'ABC Labs', {link:{'url':link}})
        # An unrelated domain is not treated as ABC Labs first-party evidence.
        self.assertEqual(facts, [])
        link = 'https://abclabs.example/imprint'
        with patch('company_facts.fetch_page', return_value=(200,None,'text/html',page)):
            facts, overview = verified_company({}, 'ABC Labs', {link:{'url':link}})
        self.assertEqual(facts[0]['value'], 'Example Holdings Ltd')
        self.assertNotIn('Kreditbank', overview)

    def test_company_unavailable_does_not_retain_guessed_parent(self):
        link = 'https://www.dkbcodefactory.com/imprint'
        with patch('company_facts.fetch_page', side_effect=TimeoutError()):
            facts, overview = verified_company({'overview':'Subsidiary of Deutsche Bank'}, 'Unknown Factory', {link:{'url':link}})
        self.assertEqual(facts, [])
        self.assertIn('could not be independently verified', overview)
        self.assertNotIn('Deutsche Bank', overview)

    def test_english_c2_is_matched_once_and_never_a_gap(self):
        cv='Built JavaScript tests.\nLanguages: English C2; German B1.'
        analysis={'score':65,'summary':'English is missing despite C2.', 'matched_skills':[],
                  'missing_skills':[{'skill':'Fluent English','reason':'CV states C2, so not missing','priority':'high'}, {'skill':'Java','reason':'Java not evidenced','priority':'high'}],
                  'improvements':['Improve your English proficiency.', 'Practice Java backend tests.']}
        result=coherent_fit(analysis,cv)
        self.assertEqual([item['skill'] for item in result['missing_skills']], ['Java'])
        self.assertEqual(result['validated_gaps'],result['missing_skills'])
        self.assertIn('English C2',result['matched_skills'][0]['evidence'])
        self.assertIn('not recalculated', result['score_consistency'])
        self.assertNotIn('Improve your English',str(result['improvements']))
        self.assertFalse(english_evidence('German C2; English B1','English'))
        self.assertFalse(english_evidence('English B1 German C2','English'))
        self.assertFalse(english_evidence('English C2 in progress','Fluent English'))
        self.assertFalse(english_evidence('English C1','English C2'))

    def test_inline_citations_are_plain_text_without_enabling_html(self):
        raw='A [source](https://example.com/about) says this [1]. \ue200cite\ue202turn0search0\ue201'
        cleaned=plain_prose(raw)
        self.assertEqual(cleaned,'A source says this .')
        self.assertEqual(plain_prose('<b>literal</b>'),'<b>literal</b>')

    def test_backend_resource_titles_match_verified_official_guides(self):
        for focus,hint,expected in [('Java objects','Oracle Java OOP','dev.java/learn/classes-objects'),('HTTP stubs','WireMock stubbing','wiremock.org/docs/stubbing'),('Backend API testing','REST Assured usage','rest-assured/wiki/Usage'),('Kotlin fundamentals','Kotlin syntax','kotlinlang.org/docs/basic-syntax')]:
            with self.subTest(focus=focus):
                resources=learning_resources({'focus':focus,'resource_hint':hint,'activities':[]})
                self.assertIn(expected,resources[0]['url'])

    def test_company_route_never_copies_wrong_overview_into_handoff(self):
        module.limits.clear()
        link='https://www.dkbcodefactory.com/imprint'
        response_data={'overview':'DKB belongs to Deutsche Bank [source](https://bad.example).','identity_facts':[], 'values':[], 'topics':[], 'questions':['Describe a quality strategy.'],'_sources':[{'url':link}]}
        with patch.dict(os.environ,{'OPENAI_API_KEY':'','APP_PASSWORD':''}), patch('company_facts.fetch_page',return_value=(200,None,'text/html',b'<p>A company of Deutsche Kreditbank AG</p>')):
            # The registration receives the original generate function, so patch provider-independent verifier output through research input.
            import io,json
            payload={'status':'completed','output':[{'type':'web_search_call','action':{'sources':[{'url':link}]}},{'type':'message','content':[{'type':'output_text','text':json.dumps(response_data),'annotations':[]}]}]}
            with patch.dict(os.environ,{'OPENAI_API_KEY':'test-only'}),patch('app.urlopen') as provider:
                provider.return_value.__enter__.return_value=io.StringIO(json.dumps(payload))
                response=module.app.test_client().post('/api/company-prep',json={'role':'QA Engineer','company':'DKB Code Factory, Germany and Spain'})
        self.assertEqual(response.status_code,200)
        self.assertIn('Deutsche Kreditbank AG',response.json['brief']['practice_context'])
        self.assertNotIn('Deutsche Bank',response.json['brief']['practice_context'])

    def test_dated_reviewed_dkb_reference_is_transparent_when_bot_blocked(self):
        with patch('company_facts.fetch_page', return_value=(503,None,'text/html',b'blocked')), patch('company_facts.date') as clock:
            clock.today.return_value = date(2026,10,21)
            clock.fromisoformat.side_effect = date.fromisoformat
            facts, overview = verified_company({}, 'DKB Code Factory, Germany and Spain', {})
        self.assertIn('Deutsche Kreditbank AG',overview)
        self.assertIn('live parent verification unavailable',overview)
        self.assertEqual(facts[0]['verification'],'reviewed_reference')

    def test_explicit_no_measured_result_remains_missing(self):
        module.limits.clear()
        source='I built an accessibility framework. I have no measured audit-time or defect reduction results.'
        story={'situation':'','task':'','action':'I built an accessibility framework.','result':'I have no measured audit-time or defect reduction results.'}
        with patch.dict(os.environ,{'OPENAI_API_KEY':'','APP_PASSWORD':''}),patch('app.generate',return_value={'story':story}):
            response=module.app.test_client().post('/api/evidence',json={'skill':'Automation','source':source})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json['story']['result'],'')
        self.assertIn('Result',response.json['missing'])

    def test_reviewed_reference_expires_instead_of_claiming_current_verification(self):
        with patch('company_facts.date') as clock:
            clock.today.return_value = date(2026,11,22)
            clock.fromisoformat.side_effect = date.fromisoformat
            facts, overview = verified_company({}, 'DKB Code Factory', {})
        self.assertEqual(facts, [])
        self.assertIn('could not be independently verified', overview)

    def test_reviewed_parent_is_available_if_other_company_page_has_no_identity(self):
        link='https://www.dkbcodefactory.com/product'
        with patch('company_facts.fetch_page', return_value=(200,None,'text/html',b'<p>Banking software engineering</p>')),patch('company_facts.date') as clock:
            clock.today.return_value=date(2026,10,21)
            clock.fromisoformat.side_effect=date.fromisoformat
            facts, overview=verified_company({},'DKB Code Factory',{link:{'url':link}})
        self.assertIn('Deutsche Kreditbank AG',overview)
        self.assertIn('live parent verification unavailable',overview)

    def test_partial_company_response_keeps_verified_identity_without_invalid_list_error(self):
        module.limits.clear()
        link='https://www.dkbcodefactory.com/imprint'
        import io,json
        payload={'status':'completed','output':[{'type':'web_search_call','action':{'sources':[{'url':link}]}},{'type':'message','content':[{'type':'output_text','text':json.dumps({'overview':'Unknown','values':{'bad':'shape'}}),'annotations':[]}]}]}
        with patch.dict(os.environ,{'OPENAI_API_KEY':'test-only','APP_PASSWORD':''}),patch('app.urlopen') as provider,patch('company_facts.fetch_page',return_value=(200,None,'text/html',b'<p>A company of Deutsche Kreditbank AG</p>')):
            provider.return_value.__enter__.return_value=io.StringIO(json.dumps(payload))
            response=module.app.test_client().post('/api/company-prep',json={'role':'QA Engineer','company':'DKB Code Factory'})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json['brief']['values'],[])
        self.assertTrue(response.json['brief']['topics'])
        self.assertTrue(all(topic['source_url'] is None and 'not a researched company fact' in topic['basis'] for topic in response.json['brief']['topics']))
        self.assertIn('coverage limit',response.json['brief']['research_coverage'])
        self.assertIn('Deutsche Kreditbank AG',response.json['brief']['practice_context'])
        self.assertIn('Role-focused candidate rehearsal',response.json['brief']['question_basis'])

    def test_rehearsal_excerpts_preserve_dotted_names_and_mark_long_quotes(self):
        from learning_scope import rehearsal_questions
        cv='Built an accessibility framework with Axe.core and Playwright. Tested releases.'
        questions=rehearsal_questions(cv,'QA Engineer')
        self.assertIn('Axe.core and Playwright.',questions[0])
        self.assertIn('Axe.core and Playwright.',questions[1])
        long='Built a Playwright framework '+('with careful checks '*25)+'.'
        quote=rehearsal_questions(long,'QA Engineer')[0].split('"')[1]
        self.assertTrue(quote.endswith('…'))
        self.assertLessEqual(len(quote),240)
        self.assertTrue(long.startswith(quote[:-1]))

    def test_pdf_line_breaks_are_marked_as_partial_quotations(self):
        from learning_scope import rehearsal_questions
        question=rehearsal_questions('Built Playwright frameworks, integrated tests into CI/CD and\nmentored the team.','QA Engineer')[0]
        self.assertIn('CI/CD and…"',question)

    def test_nonmobile_small_weeks_bound_setup_and_one_exercise(self):
        from learning_scope import scope_small_week
        for focus in ('Java basics with Selenium','Distributed systems and microservices','CI/CD checks'):
            week={'focus':focus}
            scope_small_week(week,5)
            self.assertEqual(sum(item['hours'] for item in week['activities']),5)
            self.assertIn('Setup is time-boxed',week['scope_note'])
            self.assertIn('unexecuted',week['deliverable'])
            self.assertIn('1.5 hours',week['activities'][0]['task'])

    def test_mobile_links_cover_both_official_platforms(self):
        links=learning_resources({'focus':'Mobile UI testing','resource_hint':'XCUITest and Espresso','activities':[]})
        self.assertEqual({link['url'] for link in links},{'https://developer.apple.com/documentation/XCUIAutomation','https://developer.android.com/training/testing/espresso'})

    def test_five_hour_mobile_week_scopes_one_platform_including_setup(self):
        from learning_scope import scope_mobile_week
        week={'focus':'Mobile UI testing on iOS and Android','resource_hint':'XCUITest and Espresso','activities':[{'task':'Build both suites and CI','hours':5}], 'deliverable':'Both platforms','success_check':'Run both'}
        scope_mobile_week(week,5)
        self.assertEqual(sum(item['hours'] for item in week['activities']),5)
        self.assertIn('Android',week['focus'])
        self.assertNotIn('XCUITest',week['resource_hint'])
        self.assertIn('setup',str(week['activities']).lower())
        self.assertIn('unexecuted',week['deliverable'])
        links=learning_resources(week)
        self.assertEqual(len(links),1)
        self.assertIn('developer.android.com',links[0]['url'])
        ios={'focus':'iOS UI testing','resource_hint':'XCUITest','activities':[{'task':'UI tests','hours':2}],'deliverable':'Test','success_check':'Run'}
        scope_mobile_week(ios,2)
        self.assertIn('iOS',ios['focus'])
        self.assertIn('designed test',ios['success_check'])

    def test_candidate_questions_use_cv_and_cv_stays_out_of_web_research(self):
        module.limits.clear()
        link='https://www.dkbcodefactory.com/imprint'
        import io,json
        cv='Built a Playwright accessibility framework using Axe-core. Collaborated on CI/CD checks without measured defect reduction.'
        payload={'status':'completed','output':[{'type':'web_search_call','action':{'sources':[{'url':link}]}},{'type':'message','content':[{'type':'output_text','text':json.dumps({'overview':'Company','values':[],'topics':[],'questions':['What does the company do?']}),'annotations':[]}]}]}
        with patch.dict(os.environ,{'OPENAI_API_KEY':'test-only','APP_PASSWORD':''}),patch('app.urlopen') as provider,patch('company_facts.fetch_page',return_value=(200,None,'text/html',b'<p>A company of Deutsche Kreditbank AG</p>')):
            provider.return_value.__enter__.return_value=io.StringIO(json.dumps(payload))
            response=module.app.test_client().post('/api/company-prep',json={'role':'QA Engineer','company':'DKB Code Factory','cv':cv})
            sent=json.loads(provider.call_args.args[0].data)
        self.assertEqual(response.status_code,200)
        self.assertNotIn(cv,sent['input'])
        self.assertNotIn('"cv"',sent['input'])
        self.assertIn('Playwright',str(response.json['brief']['questions']))
        self.assertIn('personally implement',str(response.json['brief']['questions']))
        self.assertNotIn('What does the company do?',str(response.json['brief']['questions']))
        self.assertIn('Playwright',response.json['brief']['practice_context'])

    def test_mobile_role_does_not_turn_a_java_week_into_mobile_ui_testing(self):
        from learning_scope import scope_mobile_week
        week={'focus':'Java classes','resource_hint':'Java object-oriented tutorial','activities':[{'task':'Create a Java work sample for a Mobile QA role.','hours':5}],'deliverable':'Java example','success_check':'Explain classes'}
        scope_mobile_week(week,5)
        self.assertEqual(week['focus'],'Java classes')
        self.assertNotIn('scope_note',week)

    def test_mobile_scope_recovers_missing_optional_ai_details(self):
        from learning_scope import scope_mobile_week
        week={'focus':'Mobile UI testing with Espresso','resource_hint':''}
        scope_mobile_week(week,5)
        self.assertTrue(week['success_check'])
        self.assertTrue(week['deliverable'])
        self.assertEqual(sum(item['hours'] for item in week['activities']),5)
