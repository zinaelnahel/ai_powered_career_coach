"""Audit regressions: handoffs, safe story recovery, citation display and resource coverage."""
import os,sys,json
from pathlib import Path
from threading import Thread
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'.vendor'))
os.environ['OPENAI_API_KEY']='audit-browser-not-a-real-key';os.environ['APP_PASSWORD']=''
from app import app
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright,expect
server=make_server('127.0.0.1',5056,app,threaded=True)
Thread(target=server.serve_forever,daemon=True).start()
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(channel='chrome',headless=True)
  page=browser.new_page(viewport={'width':1440,'height':1000})
  errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
  page.goto('http://127.0.0.1:5056',wait_until='networkidle')
  page.locator('.nav[data-page="lab"]').click();page.locator('#tab-fit').click()
  page.locator('#lab-role').fill('Senior QA Engineer')
  cv='QA engineer with JavaScript and Playwright automation experience. Built accessible web tests. Languages: English C2; German B1.'
  page.locator('#lab-cv').fill(cv)
  page.locator('#lab-description').fill('Require Java backend tests and fluent English for a QA role.')
  old={'score':65,'summary':'Context [source](https://example.com) [1].','matched_skills':[{'skill':'English proficiency','evidence':'Languages: English C2; German B1.'}],'missing_skills':[{'skill':'Fluent English','reason':'C2 is evidenced','priority':'high'},{'skill':'Java','reason':'Not evidenced','priority':'high'}],'improvements':['Practice Java.']}
  page.route('**/api/fit',lambda route:route.fulfill(status=200,content_type='application/json',body=json.dumps({'analysis':old,'demo':False})))
  page.locator('#lab-form button[type="submit"]').click()
  expect(page.locator('.lab-result-summary')).not_to_contain_text('](https')
  original_description=page.locator('#lab-description').input_value()
  for selector in ('#lab-description','#lab-role','#lab-cv'):
   original=page.locator(selector).input_value()
   page.locator(selector).fill(original+' AUDIT EDIT')
   expect(page.locator('#lab-output')).to_contain_text('rerun analysis')
   expect(page.locator('.lab-score')).to_have_count(0)
   expect(page.get_by_role('button',name='Turn this into a learning plan')).to_have_count(0)
   page.locator(selector).fill(original)
   expect(page.locator('.lab-score')).to_have_count(1)
  page.locator('#lab-description').fill('AUDIT CHANGED INPUT: Entry-level role requiring only fluent English.')
  with page.expect_download() as download_info:
   page.locator('.lab-result-heading button').click()
  exported=json.loads(Path(download_info.value.path()).read_text(encoding='utf-8'))
  assert exported['input_snapshot']['description']==original_description
  page.reload(wait_until='networkidle')
  page.locator('.nav[data-page="lab"]').click()
  expect(page.locator('#lab-output')).to_contain_text('rerun analysis')
  expect(page.locator('.lab-score')).to_have_count(0)
  page.locator('#lab-description').fill(original_description)
  page.get_by_role('button',name='Turn this into a learning plan').click()
  expect(page.locator('#lab-gaps')).to_contain_text('Java')
  assert 'English' not in page.locator('#lab-gaps').input_value()
  page.locator('#tab-company').click();page.locator('#lab-company').fill('DKB Code Factory')
  company={'overview':'Company: DKB Code Factory GmbH. Parent organization: Deutsche Kreditbank AG.','identity_facts':[],'values':[],'topics':[],'questions':['Describe a quality decision.'],'practice_context':'Company: DKB Code Factory GmbH. Parent organization: Deutsche Kreditbank AG.\nRole practice: discuss a QA project.'}
  company['research_coverage']='No supported company values were retrieved. This is a research coverage limit.'
  company['values']=[{'value':'Work abroad','evidence':'Parent-bank career context only.','source_url':'https://www.dkb.de/karriere/berufserfahrene/tech','basis':'External or parent-company context; not verified for this employer','applicability':'Applicability to DKB Code Factory in Spain has not been independently established. Ask the recruiter.'}]
  company['topics']=[{'topic':'Risk-based testing','reason':'Explain a real QA decision.','source_url':None,'basis':'Role-based suggestion; not a researched company fact'}]
  page.route('**/api/company-prep',lambda route:route.fulfill(status=200,content_type='application/json',body=json.dumps({'brief':company,'sources':[],'demo':False})))
  page.locator('#lab-form button[type="submit"]').click()
  expect(page.get_by_text(company['research_coverage'],exact=True)).to_be_visible()
  expect(page.get_by_text(company['values'][0]['applicability'],exact=True)).to_be_visible()
  expect(page.get_by_text(company['topics'][0]['basis'],exact=True)).to_be_visible()
  page.get_by_role('button',name='Practice this interview').click()
  expect(page.locator('#interview-description')).to_have_value(__import__('re').compile('Deutsche Kreditbank AG'))
  assert 'Deutsche Bank' not in page.locator('#interview-description').input_value()
  page.locator('.nav[data-page="journey"]').click()
  page.get_by_role('tab',name='Goals & stories',exact=True).click()
  source='I built an accessibility framework with Playwright. I have no quantified outcome evidence.'
  page.locator('#story-title').fill('Audit fallback example')
  page.locator('#story-skill').fill('Accessibility')
  page.locator('#story-source').fill(source)
  page.locator('#story-task').fill('Existing user draft responsibility.')
  page.get_by_label('I reviewed this story.').check()
  fallback={'demo':False,'fallback':True,'story':{'situation':source,'task':'','action':'','result':''},'missing':['Task','Action','Result'],'recovery_notice':'An extractive fallback preserves only your original source. No Result was invented.'}
  page.route('**/api/evidence',lambda route:route.fulfill(status=200,content_type='application/json',body=json.dumps(fallback)))
  page.get_by_role('button',name='Structure with AI').click()
  expect(page.locator('#story-situation')).to_have_value(source)
  expect(page.locator('#story-task')).to_have_value('Existing user draft responsibility.')
  expect(page.locator('#story-result')).to_have_value('')
  expect(page.get_by_label('I reviewed this story.')).not_to_be_checked()
  expect(page.locator('#notice')).to_contain_text('extractive fallback')
  for width in (390,320):
   page.set_viewport_size({'width':width,'height':1000})
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  assert not errors,errors
  browser.close()
 print('PASS: English removed from legacy roadmap handoff, Java retained, verified company identity reaches interview, plain citations and mobile layout.')
finally:
 server.shutdown()
