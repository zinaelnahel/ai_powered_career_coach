"""Exercise browser speech events without sending real microphone audio."""
import os
import sys
from pathlib import Path
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
server = make_server('127.0.0.1', 5054, app, threaded=True)
Thread(target=server.serve_forever, daemon=True).start()
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel='chrome', headless=True)
        page = browser.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.add_init_script("""
          window.SpeechRecognition = class {
            constructor() { window.speech = this; }
            start() { this.started = true; }
            stop() { this.onend?.(); }
            abort() { this.aborted = true; this.onend?.(); }
          };
          window.emitSpeech = (text, final) => {
            const result = [{ transcript: text }]; result.isFinal = final;
            window.speech.onresult({resultIndex: 0, results: [result]});
          };
        """)
        page.goto('http://127.0.0.1:5054')
        page.locator('#demo').check()
        page.locator('.nav[data-page="interview"]').click()
        page.locator('#interview-role').fill('Software Engineer')
        page.locator('#setup-form button').click()
        expect(page.locator('#answer')).to_be_visible()
        page.locator('#answer').fill('My existing answer.')
        page.get_by_role('button', name='Dictate answer', exact=True).click()
        expect(page.locator('#send')).to_be_disabled()
        assert page.evaluate('speech.lang') == 'en-US'
        page.evaluate("emitSpeech('I led the project', false)")
        expect(page.locator('#answer')).to_have_value('My existing answer.')
        expect(page.get_by_role('status')).to_contain_text('I led the project')
        page.evaluate("emitSpeech('I led the project.', true)")
        expect(page.locator('#answer')).to_have_value('My existing answer. I led the project.')
        page.get_by_role('button', name='Stop dictation', exact=True).click()
        expect(page.locator('#send')).to_be_enabled()
        page.locator('#answer').fill('Edited answer')
        page.locator('#dictation-language').select_option('de-DE')
        page.get_by_role('button', name='Dictate answer', exact=True).click()
        assert page.evaluate('speech.lang') == 'de-DE'
        page.evaluate("speech.onerror({error:'not-allowed'})")
        expect(page.get_by_role('status')).to_contain_text('Microphone access was denied')
        expect(page.locator('#answer')).to_have_value('Edited answer')
        page.get_by_role('button', name='Dictate answer', exact=True).click()
        page.locator('.nav[data-page="journey"]').click()
        page.get_by_role('tab', name='History & feedback', exact=True).click()
        assert page.evaluate('speech.aborted')
        page.evaluate("emitSpeech('Late event must be ignored', true)")
        page.locator('.nav[data-page="interview"]').click()
        expect(page.locator('#answer')).to_have_value('Edited answer')
        page.reload()
        page.locator('.nav[data-page="interview"]').click()
        expect(page.locator('#answer')).to_have_value('Edited answer')
        expect(page.get_by_role('button', name='Dictate answer', exact=True)).to_be_visible()
        page.locator('#demo').check()
        page.locator('#send').click()
        expect(page.locator('.message.user')).to_contain_text('Edited answer')
        page.get_by_role('button', name='Back to interview setup', exact=True).click()
        page.get_by_role('button', name='Keep practicing', exact=True).click()
        expect(page.locator('#interview-session')).to_be_visible()
        page.locator('#answer').fill('Unsent answer to discard')
        page.get_by_role('button', name='Dictate answer', exact=True).click()
        page.get_by_role('button', name='Back to interview setup', exact=True).click()
        page.get_by_role('button', name='Discard & return to setup', exact=True).click()
        expect(page.locator('#interview-setup')).to_be_visible()
        expect(page.locator('#interview-role')).to_have_value('Software Engineer')
        assert page.evaluate('speech.aborted')
        page.reload()
        page.locator('.nav[data-page="interview"]').click()
        expect(page.locator('#interview-setup')).to_be_visible()
        assert page.evaluate("JSON.parse(localStorage.getItem('career-coach-memory-v1')).memory.workspace['interview.answer']") == ''
        assert not errors, errors
        unsupported = browser.new_page()
        unsupported.add_init_script('window.SpeechRecognition = undefined; window.webkitSpeechRecognition = undefined;')
        unsupported.goto('http://127.0.0.1:5054')
        unsupported.locator('.nav[data-page="interview"]').click()
        unsupported.locator('#demo').check()
        unsupported.locator('#interview-role').fill('Software Engineer')
        unsupported.locator('#setup-form button').click()
        expect(unsupported.get_by_text('Voice dictation is unavailable in this browser.', exact=False)).to_be_visible()
        browser.close()
        print('PASS: dictation append, interim text, stop, language, permission errors, navigation cleanup, late events, saved draft, submission and unsupported browser fallback.')
finally:
    server.shutdown()
