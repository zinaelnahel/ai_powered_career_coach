"""Focused accessibility regression checks; not a full WCAG conformance audit."""
import os
import sys
import json
from pathlib import Path
from threading import Thread
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT / '.vendor'))
os.environ['OPENAI_API_KEY']='accessibility-test-not-a-key'
os.environ['APP_PASSWORD']=''
from app import app
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright, expect
server=make_server('127.0.0.1',5057,app,threaded=True)
Thread(target=server.serve_forever,daemon=True).start()
AUDIT = r"""() => {
 const parse=s=>s.match(/[\d.]+/g).map(Number);
 const luminance=rgb=>rgb.slice(0,3).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4}).reduce((sum,v,i)=>sum+v*[.2126,.7152,.0722][i],0);
 const contrast=(a,b)=>(Math.max(luminance(a),luminance(b))+.05)/(Math.min(luminance(a),luminance(b))+.05);
 const problems=[];
 const walker=document.createTreeWalker(document.querySelector('.dojo-theme'),NodeFilter.SHOW_TEXT);
 while(walker.nextNode()) {
  const node=walker.currentNode, el=node.parentElement;
  if(!node.textContent.trim() || !el.checkVisibility() || el.closest('svg,script,style,button:disabled,[hidden]'))continue;
  const cs=getComputedStyle(el),size=parseFloat(cs.fontSize);
  if(size<12)problems.push({type:'small-text',text:node.textContent.trim().slice(0,70),size});
  let parent=el,bg=[255,255,255];
  while(parent){const value=parse(getComputedStyle(parent).backgroundColor);if(value.length===3||value[3]===1){bg=value;break}parent=parent.parentElement;}
  const fg=parse(cs.color), ratio=contrast(fg,bg), required=size>=24 || (size>=18.66 && parseInt(cs.fontWeight)>=700)?3:4.5;
  if(ratio<required)problems.push({type:'contrast',text:node.textContent.trim().slice(0,65),ratio:Math.round(ratio*100)/100,required,color:cs.color});
 }
 const smallButtons=[...document.querySelectorAll('button')].filter(e=>e.checkVisibility()&&!e.disabled).filter(e=>{const r=e.getBoundingClientRect();return r.height<43.9||r.width<43.9}).map(e=>e.innerText.trim());
 return {problems,smallButtons,overflow:document.documentElement.scrollWidth>innerWidth+1};
}"""
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(channel='chrome',headless=True)
  page=browser.new_page(viewport={'width':1440,'height':1000})
  errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
  page.goto('http://127.0.0.1:5057',wait_until='networkidle')
  page.keyboard.press('Tab')
  expect(page.get_by_role('link',name='Skip to main content')).to_be_focused()
  page.keyboard.press('Enter')
  expect(page.locator('#main-content')).to_be_focused()
  failures=[]
  for width in [1440,390,320]:
   page.set_viewport_size({'width':width,'height':1000})
   for section in ['overview','interview','cv','lab','journey','about']:
    if section=='about':page.get_by_role('button',name='About this app',exact=True).click()
    else:page.locator('.nav[data-page="'+section+'"]').click()
    result=page.evaluate(AUDIT)
    if result['problems'] or result['smallButtons'] or result['overflow']:
     failures.append({'width':width,'section':section,**result})
   if width==1440:
    page.locator('.nav[data-page="journey"]').click()
    for tab in ['History & feedback','Goals & stories','Data settings']:
     page.get_by_role('tab',name=tab,exact=True).click()
     result=page.evaluate(AUDIT)
     if result['problems'] or result['smallButtons']:failures.append({'width':width,'section':tab,**result})
   page.locator('.nav[data-page="overview"]').click()
   page.screenshot(path=str(ROOT / ('artifacts/accessibility-'+str(width)+'.png')),full_page=True)
  page.set_viewport_size({'width':1440,'height':1000})
  def audit_state(section):
   result=page.evaluate(AUDIT)
   if result['problems'] or result['smallButtons'] or result['overflow']:failures.append({'width':1440,'section':section,**result})
  page.locator('#demo').check()
  page.locator('.nav[data-page="interview"]').click()
  page.locator('#interview-role').fill('QA Engineer')
  page.locator('#question-count').select_option('3')
  page.locator('#setup-form button').click()
  expect(page.locator('#answer')).to_be_visible()
  audit_state('Interview conversation')
  for index in range(3):
   page.locator('#answer').fill('I built and tested accessible React applications for 200 users.')
   page.locator('#send').click()
   if index<2:expect(page.locator('.message.assistant')).to_have_count(index+2)
  expect(page.locator('#interview-report')).to_be_visible()
  audit_state('Interview feedback')
  page.locator('.nav[data-page="cv"]').click()
  page.locator('#cv-role').fill('QA Engineer')
  cv='I built accessible React applications for 200 users. Skills: Python, React, SQL and testing. Education: Computer Science.'
  page.locator('#cv-text').fill(cv)
  page.locator('#cv-form button[type="submit"]').click()
  expect(page.locator('#cv-report')).to_be_visible()
  audit_state('CV feedback')
  page.locator('.nav[data-page="lab"]').click()
  page.locator('#lab-role').fill('QA Engineer')
  page.locator('#lab-form button[type="submit"]').click()
  expect(page.locator('.lab-job')).to_have_count(1)
  audit_state('Jobs results')
  page.locator('#tab-fit').click()
  page.locator('#lab-cv').fill(cv)
  page.locator('#lab-description').fill('We require React, Python, SQL and testing skills to build accessible software.')
  page.locator('#lab-form button[type="submit"]').click()
  expect(page.locator('.lab-score')).to_be_visible()
  audit_state('Fit results')
  page.locator('#tab-roadmap').click()
  page.locator('#lab-weeks').fill('1')
  page.locator('#lab-form button[type="submit"]').click()
  expect(page.locator('.lab-week')).to_have_count(1)
  audit_state('Roadmap results')
  page.locator('#tab-company').click()
  page.locator('#lab-company').fill('Example Company')
  page.locator('#lab-form button[type="submit"]').click()
  expect(page.locator('#lab-output')).to_contain_text('No company research was performed')
  audit_state('Company results')
  page.locator('.nav[data-page="journey"]').click()
  page.get_by_role('tab',name='History & feedback',exact=True).click()
  audit_state('Saved reports')
  page.emulate_media(reduced_motion='reduce')
  assert page.locator('.dojo-room').first.evaluate('(el)=>getComputedStyle(el).transitionDuration')=='0s'
  assert not errors, errors
  assert page.request.get('http://127.0.0.1:5057/favicon.ico').status==200
  browser.close()
  if failures:
   unique={item['text']:item for failure in failures for item in failure['problems']}
   print(json.dumps({'issues':list(unique.values()),'smallButtons':[item for failure in failures for item in failure['smallButtons']], 'overflow':[(failure['width'],failure['section']) for failure in failures if failure['overflow']]}),flush=True)
   raise AssertionError('Accessibility regression checks failed.')
  print('PASS: visible text >=12px, sampled solid-background text contrast, 44px buttons, skip-link focus, reduced motion, icons and 1440/390/320px layouts.',flush=True)
finally:
 server.shutdown()
