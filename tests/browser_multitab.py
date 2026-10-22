"""Cross-tab regression: stale saves, simultaneous history writes and erasure."""
import os
import sys
import logging
from pathlib import Path
from threading import Thread

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / '.vendor'))
os.environ['OPENAI_API_KEY'] = ''
os.environ['APP_PASSWORD'] = ''
from app import app
# Local development configuration can load a key at import; this suite is demo-only.
os.environ['OPENAI_API_KEY'] = ''
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright, expect
logging.getLogger('werkzeug').setLevel(logging.ERROR)

server = make_server('127.0.0.1', 5059, app, threaded=True)
Thread(target=server.serve_forever, daemon=True).start()
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel='chrome', headless=True)
        context = browser.new_context()
        first, second = context.new_page(), context.new_page()
        errors = []
        for page in (first, second):
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.add_init_script("window.addEventListener('storage', e => { if (window.pauseStorage) e.stopImmediatePropagation(); });")
            page.goto('http://127.0.0.1:5059')
            page.locator('#demo').check()
            page.locator('.nav[data-page="lab"]').click()
        second.evaluate('window.pauseStorage = true')
        first.get_by_role('tab', name='Learning plan', exact=True).click()
        first.locator('#lab-role').fill('QA Engineer')
        first.locator('#lab-gaps').fill('LLM evaluation')
        first.locator('#lab-form button[type="submit"]').click()
        expect(first.locator('#lab-history option')).to_have_count(2)
        # This tab did not receive the other tab's storage events.
        second.get_by_role('tab', name='Find jobs', exact=True).click()
        second.locator('#lab-role').fill('Senior QA Engineer')
        second.locator('#lab-location').fill('Spain')
        second.locator('#lab-form button[type="submit"]').click()
        expect(second.locator('#lab-history option')).to_have_count(3)
        expect(first.locator('#tab-roadmap')).to_have_attribute('aria-selected', 'true')
        expect(first.locator('#lab-role')).to_have_value('QA Engineer')
        first.reload()
        first.locator('.nav[data-page="lab"]').click()
        expect(first.locator('#tab-roadmap')).to_have_attribute('aria-selected', 'true')
        expect(first.locator('#lab-role')).to_have_value('QA Engineer')
        expect(first.locator('#lab-history')).to_contain_text('Learning plan')
        expect(first.locator('#lab-history')).to_contain_text('Find jobs')
        # Both tabs attempt a history append on the same scheduled tick.
        for page in (first, second):
            page.get_by_role('tab', name='Find jobs', exact=True).click()
        deadline = first.evaluate('Date.now() + 700')
        for page in (first, second):
            page.evaluate('(deadline) => setTimeout(() => document.querySelector("#lab-form").requestSubmit(), Math.max(0, deadline-Date.now()))', deadline)
        first.wait_for_function("() => JSON.parse(localStorage.getItem('career-coach-memory-v1')).memory.workspace['lab.history'].length === 4")
        second.reload()
        second.locator('.nav[data-page="lab"]').click()
        expect(second.locator('#lab-history option')).to_have_count(5)
        expect(second.locator('#lab-role')).to_have_value('Senior QA Engineer')
        first.get_by_role('tab', name='Learning plan', exact=True).click()
        expect(second.locator('#tab-jobs')).to_have_attribute('aria-selected', 'true')
        first.locator('#lab-role').fill('AI QA Engineer')
        expect(second.locator('#lab-role')).to_have_value('Senior QA Engineer')
        # Saving-off preference propagates; editing another tab cannot re-enable it.
        first.get_by_role('button', name='Device saving on', exact=True).click()
        first.get_by_label('Remember on this device').uncheck()
        expect(second.get_by_role('button', name='Device saving off', exact=True)).to_be_visible()
        second.locator('#lab-role').fill('Unsaved role')
        assert second.evaluate("localStorage.getItem('career-coach-memory-v1')") is None
        # Re-enable, then delete everything in the other tab and verify no resurrection.
        first.get_by_label('Remember on this device').check()
        late_responses = []
        second.route('**/api/jobs', lambda route: late_responses.append(route))
        second.locator('#lab-form button[type="submit"]').click()
        first.get_by_role('button', name='Delete all saved data', exact=True).click()
        first.get_by_role('button', name='Delete all', exact=True).click()
        expect(first.locator('#lab-role')).to_have_value('')
        expect(second.locator('#lab-role')).to_have_value('')
        assert late_responses, 'Expected a held request before deletion'
        late_responses[0].fulfill(json={'jobs': [], 'sources': [], 'demo': True, 'summary': 'Late response after deletion'})
        expect(second.locator('#lab-form button[type="submit"]')).to_be_enabled()
        expect(second.locator('#lab-history option')).to_have_count(1)
        second.locator('#lab-role').fill('New visit only')
        assert second.evaluate("localStorage.getItem('career-coach-memory-v1')") is None
        second.reload()
        second.locator('.nav[data-page="lab"]').click()
        expect(second.locator('#lab-history option')).to_have_count(1)
        assert not errors, errors
        browser.close()
        print('PASS: stale tab and simultaneous saves preserve history; saving-off and full erasure propagate without resurrection.')
finally:
    server.shutdown()
