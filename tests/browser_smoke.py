"""Optional browser QA: pip install playwright; uses an existing Chrome install."""
import os
import re
import json
from pathlib import Path
import sys
from threading import Thread

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / '.vendor'))
os.environ['OPENAI_API_KEY'] = ''
os.environ['APP_PASSWORD'] = ''
from app import app
# Keep this demo suite independent of any local .env API credentials.
os.environ['OPENAI_API_KEY'] = ''
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright, expect


server = make_server('127.0.0.1', 5051, app, threaded=True)
thread = Thread(target=server.serve_forever, daemon=True)
thread.start()
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel='chrome', headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1100}, device_scale_factor=1)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto('http://127.0.0.1:5051')
        expect(page.locator('#connection')).not_to_contain_text('Checking AI')
        page.locator('#demo').check()
        expect(page.locator('.brand-name')).to_contain_text('Career Dojo')
        page.evaluate('document.fonts.ready')
        assert page.evaluate('document.fonts.check(\'400 16px "Roboto"\')')
        assert page.locator('h1:visible').evaluate('(el) => getComputedStyle(el).fontFamily').startswith('Roboto')
        assert page.locator('h1:visible').inner_text().startswith('Welcome to your dojo')
        (ROOT / 'artifacts').mkdir(exist_ok=True)
        page.screenshot(path=str(ROOT / 'artifacts/overview-desktop.png'), full_page=True)
        page.locator('.nav[data-page="interview"]').click()
        page.locator('#interview-role').fill('Frontend Developer')
        page.locator('#question-count').select_option('3')
        page.locator('#setup-form button').click()
        page.locator('#answer').wait_for(state='visible')
        for index in range(3):
            page.locator('#answer').fill('I built accessible React dashboards for 200 users and improved performance by 30 percent through profiling.')
            page.locator('#send').click()
            if index < 2:
                expect(page.locator('.message.assistant')).to_have_count(index + 2)
                page.locator('#send').wait_for(state='visible')
        page.locator('#interview-report').wait_for(state='visible')
        assert page.locator('#interview-report .score strong').inner_text().isdigit()
        page.locator('.nav[data-page="cv"]').click()
        page.locator('#cv-role').fill('Frontend Developer')
        page.locator('#cv-text').fill('Software engineer with 3 years of experience. Built accessible React dashboards for 200 users. Improved performance by 30 percent. Education: BSc Computer Science. Skills: React, Python, accessibility.')
        cv_text = page.locator('#cv-text').input_value()
        page.locator('#cv-file').set_input_files({'name': 'my-cv.txt', 'mimeType': 'text/plain', 'buffer': cv_text.encode()})
        expect(page.locator('#file-label')).to_have_text('my-cv.txt')
        expect(page.locator('#cv-text')).to_have_value(cv_text)
        page.locator('#cv-form button').click()
        page.locator('#cv-report').wait_for(state='visible')
        page.locator('.nav[data-page="journey"]').click()
        page.get_by_role('tab', name='History & feedback', exact=True).click()
        assert page.locator('.history-row').count() == 2
        page.locator('.history-row').first.get_by_text('View feedback').click()
        page.locator('#cv-report').wait_for(state='visible')
        with page.expect_download() as download:
            page.locator('#cv-report').get_by_text('Download feedback').click()
        assert download.value.suggested_filename == 'ai-career-coach-feedback.txt'
        # Verify React preserves drafts on provider failure and while navigating.
        page.locator('.nav[data-page="interview"]').click()
        page.locator('#interview-report').get_by_role('button', name='Practice again').click()
        page.locator('#setup-form button').click()
        page.locator('#answer').fill('I led a team of 5 people and reduced release time by 20 percent.')
        saved_answer = page.locator('#answer').input_value()
        page.route('**/api/interview', lambda route: route.fulfill(status=503, content_type='application/json', body='{"error":"Temporary provider failure. Please retry."}'))
        page.locator('#send').click()
        expect(page.locator('#notice')).to_contain_text('Temporary provider failure')
        expect(page.locator('#answer')).to_have_value(saved_answer)
        expect(page.locator('.message.assistant')).to_have_count(1)
        page.unroute('**/api/interview')
        page.locator('.nav[data-page="cv"]').click()
        page.locator('.nav[data-page="interview"]').click()
        expect(page.locator('#answer')).to_have_value(saved_answer)
        page.locator('#answer').press('Control+Enter')
        expect(page.locator('.message.assistant')).to_have_count(2)
        page.locator('#finish').click()
        page.locator('#interview-report').wait_for(state='visible')
        # All four Career Lab tools and their connected handoffs.
        page.locator('.nav[data-page="lab"]').click()
        page.locator('#tab-jobs').focus()
        page.locator('#tab-jobs').press('ArrowRight')
        expect(page.locator('#tab-fit')).to_have_attribute('aria-selected', 'true')
        page.locator('#tab-fit').press('ArrowLeft')
        page.locator('#lab-role').fill('Frontend Developer')
        page.locator('#lab-location').fill('Berlin')
        page.locator('#lab-form button[type="submit"]').click()
        expect(page.locator('#lab-output')).to_contain_text('FICTIONAL SAMPLE')
        assert page.locator('#lab-output a').count() == 0
        page.locator('#lab-output').get_by_role('button', name='Check my fit').click()
        page.locator('#lab-form').get_by_role('button', name='Use latest CV review').click()
        expect(page.locator('#lab-cv')).to_have_value(cv_text)
        page.locator('#lab-description').fill('We require React, Python, SQL and accessibility for a customer-facing frontend developer role.')
        page.get_by_label('I checked the source and included the full requirements.').check()
        page.locator('#lab-form button[type="submit"]').click()
        expect(page.locator('#lab-output')).to_contain_text('Requirements not yet evidenced')
        expect(page.locator('#lab-output')).to_contain_text('python')
        page.locator('#lab-output').get_by_role('button', name='Turn this into a learning plan').click()
        expect(page.locator('#lab-gaps')).to_have_value(re.compile('sql', re.I))
        page.locator('#lab-form').get_by_role('button', name='Use interview feedback').click()
        expect(page.locator('#lab-feedback')).not_to_have_value('')
        page.locator('#lab-weeks').fill('3')
        page.locator('#lab-hours').fill('2')
        page.locator('#lab-form button[type="submit"]').click()
        expect(page.locator('.lab-week')).to_have_count(3)
        page.locator('.lab-check input').first.click()
        expect(page.locator('.lab-check input').first).to_be_checked()
        expect(page.locator('#lab-output')).to_contain_text('1 milestones checked off')
        with page.expect_download() as lab_download:
            page.locator('#lab-output').get_by_role('button', name='Download').click()
        assert lab_download.value.suggested_filename == 'ai-career-coach-roadmap.json'
        downloaded = json.loads(Path(lab_download.value.path()).read_text(encoding='utf-8'))
        assert len(downloaded['plan']['weeks']) == 3
        assert downloaded['demo'] is True
        page.locator('#tab-company').click()
        page.locator('#lab-company').fill('Example Company')
        page.locator('#lab-form button[type="submit"]').click()
        expect(page.locator('#lab-output')).to_contain_text('No company research was performed')
        page.locator('#lab-output').get_by_role('button', name='Practice this interview').click()
        expect(page.locator('#interview-description')).to_have_value(re.compile('Company: Example Company'))
        page.locator('.nav[data-page="overview"]').click()
        page.set_viewport_size({'width': 390, 'height': 844})
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        page.screenshot(path=str(ROOT / 'artifacts/overview-mobile.png'), full_page=True)
        page.locator('.nav[data-page="lab"]').click()
        page.locator('#tab-roadmap').click()
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        page.screenshot(path=str(ROOT / 'artifacts/career-lab-mobile.png'), full_page=True)
        assert not errors, errors
        print('PASS: core flows plus all 4 Career Lab tools, CV reuse, job-to-fit, roadmap handoff, company-to-interview, mobile; no JavaScript errors')
        browser.close()
finally:
    server.shutdown()
