"""Scope small mobile-learning milestones and candidate-focused rehearsal."""
import re

IOS_URL = 'https://developer.apple.com/documentation/XCUIAutomation'
ANDROID_URL = 'https://developer.android.com/training/testing/espresso'


def mobile_resources(topic):
    links=[]
    if re.search(r'xcuitest|xctest|xcuiautomation|\bios\b',topic,re.I):
        links.append({'title':'Apple: XCTest UI testing with XCUIAutomation','url':IOS_URL})
    if re.search(r'espresso|\bandroid\b',topic,re.I):
        links.append({'title':'Android Developers: Espresso UI testing','url':ANDROID_URL})
    return links


def scope_mobile_week(week, hours):
    topic=' '.join(str(week.get(key, '') or '') for key in ('focus','resource_hint','deliverable'))
    if hours>5 or not re.search(r'mobile|xcuitest|xctest|xcuiautomation|espresso|\bios\b|\bandroid\b',str(week.get('focus', '') or '')+' '+str(week.get('resource_hint', '') or ''),re.I):
        return
    focus_links=mobile_resources(str(week.get('focus', '') or ''))
    links=focus_links or mobile_resources(topic)
    ios=len(links)==1 and links[0]['url']==IOS_URL
    platform,tool=('iOS','XCUITest') if ios else ('Android','Espresso')
    week['focus']=f'{platform} UI testing: one small {tool} exercise'
    week['resource_hint']=f'{tool} official UI testing documentation'
    week['scope_note']='One platform only. Use an existing sample app; the other platform is optional future work outside this weekly budget.'
    if hours<3:
        week['activities']=[{'task':f'Read one {tool} sample and specify one interaction and one expected UI assertion for an existing {platform} sample app. Do not set up a second platform.', 'hours':hours}]
        week['deliverable']='One annotated UI test example and a short test specification.'
        week['success_check']='Explain the interaction, assertion and prerequisites; distinguish a designed test from an executed test.'
    else:
        setup=1 if hours<=4 else 1.5
        week['activities']=[{'task':f'Time-box prerequisites and opening an existing {platform} sample app to {setup} hours. If blocked, record the blocker and continue with a test sketch.', 'hours':setup},
                            {'task':f'Adapt one {tool} UI test: one interaction and one assertion. Use a single emulator/simulator; no CI or second-platform setup.', 'hours':hours-setup-1},
                            {'task':'Rerun the single test and record the result, or document the tooling blocker and an annotated test sketch. Stop at the weekly time limit.', 'hours':1}]
        week['deliverable']='One small UI test plus a run log, or a clearly labelled unexecuted test sketch and setup-blocker notes.'
        week['success_check']='Show one passing interaction/assertion or explain the unresolved setup blocker without claiming the test ran.'


def rehearsal_questions(cv,role):
    prompts=[]
    categories=[(r'\bplaywright\b|\bcypress\b|\bselenium\b','What did you personally implement, and how did you keep the tests reliable?'),
                (r'axe.core|accessibility','How did you decide what to automate and what required manual accessibility checks?'),
                (r'ci/cd|continuous integration','How did you handle flaky checks or failed builds, and what trade-offs did you make?'),
                (r'\bapi\b|backend','How did you choose test boundaries, mocks and failure cases?')]
    for pattern,question in categories:
        match=re.search(pattern,cv,re.I)
        if not match: continue
        # Dots inside names such as Axe.core are not sentence boundaries.
        boundaries=list(re.finditer(r'\n|[.!?](?=\s|$)',cv))
        start=max([boundary.end() for boundary in boundaries if boundary.end()<=match.start()],default=0)
        end=next((boundary.end() for boundary in boundaries if boundary.start()>=match.end()),len(cv))
        excerpt=cv[start:end].strip()
        if len(excerpt)>240:
            excerpt=excerpt[:237].rsplit(' ',1)[0].rstrip(' ,;:')+'…'
        elif excerpt and excerpt[-1] not in '.!?…':
            excerpt+='…'
        prompts.append(f'Your CV states: "{excerpt}" {question} Use only real examples; if you did not perform a step, say so.')
        if len(prompts)==3: break
    if re.search(r'\bqa\b|test|quality',role,re.I):
        prompts += ['Describe a QA project where you prioritized risks. What was your individual decision and why?',
                    'What outcome evidence, if any, did you collect for a testing improvement? Explain what remains unmeasured.']
    else:
        prompts += [f'Describe a project relevant to {role}. What did you personally do, and what trade-off did you make?',
                    'What evidence supports the outcome, and what remains uncertain?']
    return prompts[:5]


def scope_small_week(week, hours):
    """Bound non-mobile exercises without assuming a working development setup."""
    if hours>5 or week.get('scope_note'):
        return
    focus=str(week.get('focus',''))
    if not focus:
        return
    if not isinstance(week.get('resource_hint'),str) or not week['resource_hint'].strip():
        week['resource_hint']=f'Official documentation: {focus}'
    if re.search(r'distributed|microservice|fault.toleran|resilien|timeout|retr(?:y|ies)',focus,re.I):
        sample='a single-file dependency stub with one normal response and one simulated timeout (no microservices deployment)'
        exercise='Specify one timeout/retry expectation and exercise only that failure case against the stub'
        week['resource_hint']='Google SRE: Testing for Reliability'
    elif re.search(r'mock|stub|virtuali[sz]',focus,re.I):
        sample='one local WireMock stub returning a fixed JSON response for GET /status'
        exercise='Configure that single stub response, call GET /status and assert the client handles its status and JSON body'
        week['resource_hint']='WireMock: stubbing'
    elif re.search(r'\bapi\b|rest.?assured|\bhttp\b',focus,re.I):
        sample='one local stub endpoint GET /status returning HTTP 200 and JSON {"ok": true}; use an existing REST Assured project or an unexecuted test sketch'
        exercise='Send one HTTP GET request and assert status 200 and body field ok=true; defer authentication suites, new frameworks and extra endpoints'
        week['resource_hint']='REST Assured: usage guide'
    elif re.search(r'\bjava\b|\bkotlin\b',focus,re.I):
        sample='one small function from the official language documentation in an existing editor or browser playground'
        exercise='Adapt that one function and check one normal input and one boundary input; defer Selenium and framework setup'
    else:
        sample=f'one existing documentation example or a one-page worked example for {focus}'
        exercise='Adapt one small example for this focus and check one expected result; defer extra tools, integrations and full projects'
    week['scope_note']='One example and one learning objective only. Setup is time-boxed; an annotated, unexecuted design is acceptable if tools block progress. Stop at the weekly budget.'
    if hours<3:
        week['activities']=[{'task':f'Read and annotate {sample}. Write one expected result; do not install a new toolchain.', 'hours':hours}]
    else:
        setup=1 if hours<=4 else 1.5
        week['activities']=[{'task':f'Within {setup} hours select/open {sample}. If setup fails, record the blocker and continue on paper.', 'hours':setup},
                            {'task':exercise+'. If blocked, write an explicitly unexecuted test/design instead.', 'hours':hours-setup-1},
                            {'task':'Record the observed result or the unexecuted design and setup blocker. Explain one decision and stop at the time limit.', 'hours':1}]
    week['deliverable']='One annotated example with one expected result, plus a run log or clearly labelled unexecuted design and blocker notes.'
    week['success_check']=exercise+'. Show the expected assertion and observed result, or label the design unexecuted and explain the tooling blocker. No second framework or full system is required.'
