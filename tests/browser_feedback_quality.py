"""Regression checks for report coverage, score explanations, search messaging and privacy."""
import os
import sys
import json
from pathlib import Path
from threading import Thread
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT / '.vendor'))
os.environ['OPENAI_API_KEY']='browser-quality-not-a-real-key'
os.environ['APP_PASSWORD']=''
from app import app
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright, expect
server=make_server('127.0.0.1',5058,app,threaded=True)
Thread(target=server.serve_forever,daemon=True).start()
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(channel='chrome',headless=True)
  page=browser.new_page(viewport={'width':1440,'height':1000})
  errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
  page.goto('http://127.0.0.1:5058',wait_until='networkidle')
  expect(page.get_by_role('button',name='Device saving on',exact=True)).to_be_visible()
  expect(page.locator('#data-use-note')).to_contain_text('Live AI sends submitted content to OpenAI')
  assert 'Private session' not in page.locator('body').inner_text()
  page.locator('#demo').check()
  page.locator('.nav[data-page="interview"]').click()
  page.locator('#interview-role').fill('QA Engineer')
  page.locator('#setup-form button').click()
  page.locator('#answer').fill('I built CI/CD test pipelines for 200 users and monitored failures.')
  page.locator('#send').click()
  expect(page.locator('.message.assistant')).to_have_count(2)
  page.locator('#finish').click()
  expect(page.locator('.assessment-coverage')).to_contain_text('Partial session: 1 of 5 questions answered')
  expect(page.locator('.score-explanation')).to_contain_text('Demo rule')
  with page.expect_download() as download:
   page.get_by_role('button',name='Download feedback',exact=False).click()
  exported=Path(download.value.path()).read_text(encoding='utf-8')
  assert 'Partial session: 1 of 5 questions answered' in exported
  assert 'SCORE EXPLANATION' in exported
  page.reload()
  page.locator('.nav[data-page="journey"]').click()
  page.get_by_role('button',name='View feedback',exact=True).click()
  expect(page.locator('.assessment-coverage')).to_contain_text('Partial session: 1 of 5')
  page.get_by_role('button',name='Device saving on',exact=True).click()
  expect(page.locator('#journey-settings')).to_be_visible()
  page.get_by_label('Remember on this device').uncheck()
  expect(page.get_by_role('button',name='Device saving off',exact=True)).to_be_visible()
  expect(page.locator('#data-use-note')).to_contain_text('Device saving is off')
  page.get_by_label('Remember on this device').check()
  # An old record still opens without invented coverage or rationale.
  page.evaluate("""() => {
   const key='career-coach-memory-v1', saved=JSON.parse(localStorage.getItem(key));
   const record=JSON.parse(JSON.stringify(saved.memory.sessions[0]));
   record.role='Legacy interview';delete record.assessment;delete record.context.total;delete record.report.score_explanation;
   saved.memory.sessions.push(record);localStorage.setItem(key,JSON.stringify(saved));
  }""")
  page.reload()
  page.locator('.nav[data-page="journey"]').click()
  page.locator('.history-row').filter(has=page.get_by_role('heading',name='Legacy interview',exact=True)).get_by_role('button',name='View feedback',exact=True).click()
  expect(page.locator('.assessment-coverage')).to_contain_text('Original session length was not recorded')
  expect(page.locator('.score-explanation')).to_contain_text('older report')
  # Even a cached/unfiltered old provider summary cannot contradict empty cards.
  page.route('**/api/jobs',lambda route:route.fulfill(status=200,content_type='application/json',body=json.dumps({'summary':'I found several Senior QA Engineer positions.', 'jobs':[], 'sources':[{'title':'Unrelated SRE research','url':'https://example.test/sre'}], 'demo':False})))
  page.locator('.nav[data-page="lab"]').click()
  page.locator('#lab-role').fill('Senior QA Engineer')
  page.locator('#lab-form button[type="submit"]').click()
  expect(page.locator('#lab-output')).to_contain_text('No source-backed job listings could be confirmed')
  expect(page.locator('#lab-output')).not_to_contain_text('I found several')
  expect(page.locator('#lab-output')).not_to_contain_text('Unrelated SRE')
  expect(page.locator('#lab-output a')).to_have_count(0)
  page.unroute('**/api/jobs')
  page.locator('.nav[data-page="cv"]').click()
  text='CORE SKILLS\nTesting: Playwright, Cypress and CI/CD.\nEXPERIENCE\n\x7f Built testing tools for 200 users.\nExpected graduation: November 2026.'
  page.locator('#cv-file').set_input_files({'name':'qa-cv.txt','mimeType':'text/plain','buffer':text.encode()})
  expect(page.locator('#cv-text')).to_contain_text('- Built testing tools for 200 users.')
  expect(page.locator('#cv-text')).to_contain_text('Expected graduation: November 2026.')
  assert not errors,errors
  browser.close()
  print('PASS: partial coverage and score rationale persist/export, legacy reports, saving status and disclosure, search contradictions and conservative extraction.')
finally:
 server.shutdown()
