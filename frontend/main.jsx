import CharacterGuide from './CharacterGuide.jsx';
import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import 'bootstrap/dist/css/bootstrap.min.css';
import '../public/static/style.css';
import '../public/static/playful.css';
import './bootstrap-theme.css';
import About from './About.jsx';
import DojoOverview from './DojoOverview.jsx';
import { DojoMark } from './DojoArt.jsx';
import { DojoIcon } from './DojoIcons.jsx';
import Dictation from './Dictation.jsx';
import CareerLab from './CareerLab.jsx';
import { MemoryIcon } from './MemoryArt.jsx';
import CareerMemory from './CareerMemory.jsx';
import { useCareerMemory, useWorkspaceState } from './memory.js';
import './career-lab.css';
import '@fontsource/roboto/latin-400.css';
import '@fontsource/roboto/latin-500.css';
import '@fontsource/roboto/latin-700.css';
import '@fontsource/roboto/latin-900.css';
import './typography.css';
import './dojo.css';
import './accessibility.css';

const pages = { overview: 'Overview', interview: 'Mock interview', cv: 'CV reviewer', lab: 'Career Lab', journey: 'My journey' };

// PSEUDOCODE: API TRANSPORT
// SEND JSON or multipart form data to a same-origin Flask route.
// PARSE the response and throw a readable error for failures.
async function api(path, data) {
  const file = data instanceof FormData;
  const response = await fetch(path, { method: 'POST', ...(file ? { body: data } : { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }) });
  let result;
  try { result = await response.json(); } catch { throw new Error('The server could not complete the request. Please retry.'); }
  if (!response.ok) throw new Error(result.error || 'Something went wrong. Please retry.');
  return result;
}

function Action({ busy, children, className = '', ...props }) {
  return <button className={`btn primary ${className}`} disabled={busy} {...props}>{busy && <span className="spinner-border spinner-border-sm" aria-hidden="true" />}{children}</button>;
}

function Field({ id, label, optional, children }) {
  return <div className="mb-3"><label className="form-label" htmlFor={id}>{label} {optional ? <small>Optional</small> : <span>*</span>}</label>{children}</div>;
}

function Tip({ cv = false }) {
  return <aside className="tip-panel"><span className="spark">✦</span><h3>{cv ? <>Make the relevant<br />things shine.</> : <>A conversation,<br />not a pop quiz.</>}</h3><p>{cv ? 'Get specific feedback on what’s working and what could tell a stronger story.' : 'You’ll get one question at a time, with space to think and answer in your own words.'}</p><ul>{(cv ? ['Content, clarity and relevant skills', 'Stronger achievement statements', 'Errors and opportunities to improve', 'Concrete next steps for your application'] : ['Use real examples from your experience.', 'Explain your actions and their impact.', 'Get a score and practical feedback at the end.']).map(item => <li key={item}>{item}</li>)}</ul><small>{cv ? 'We review extracted text. Check fonts, spacing and visual layout in your original document.' : 'In live mode, your answers are sent to OpenAI. Your transcript and feedback are saved on this device when saving is enabled.'}</small></aside>;
}

// PSEUDOCODE: REPORT PRESENTATION
// RENDER score, summary, strengths, improvements and next steps.
// SHOW stored interview questions/answers when available.
// ALLOW another attempt or a text download of feedback and transcript.
function Report({ record, restart, id }) {
  const { report: r } = record;
  const assessment = record.assessment;
  const answeredCount = record.context?.messages?.filter(message => message.role === 'user').length;
  const coverage = assessment ? `${assessment.partial ? 'Partial session' : 'Completed session'}: ${assessment.answered} of ${assessment.total} questions answered` : record.type === 'Mock interview' ? (answeredCount ? `Saved interview: ${answeredCount} answered questions. Original session length was not recorded.` : 'Original session coverage was not recorded for this older report.') : '';
  const scoreNote = record.demo ? 'Illustrative rule-based score, not an AI assessment.' : 'AI-generated practice score. It is not standardized and does not predict hiring outcomes.';
  function download() {
    const text = [`AI Career Coach — ${record.type}`, record.role, record.demo ? 'DEMO: illustrative rule-based feedback' : 'Live AI feedback', `Score: ${r.score}/100`, scoreNote, coverage, r.summary, '\nSCORE EXPLANATION', r.score_explanation || 'This older report has no separate score explanation.', ...['strengths', 'improvements', 'next_steps'].flatMap(key => ['\n' + key.replace('_', ' ').toUpperCase(), ...r[key].map(item => `• ${item}`)]), ...(record.context?.messages || []).map(m => `\n${m.role === 'assistant' ? 'INTERVIEWER' : 'YOU'}: ${m.content}`)].join('\n');
    const url = URL.createObjectURL(new Blob([text], { type: 'text/plain;charset=utf-8' }));
    const anchor = document.createElement('a'); anchor.href = url; anchor.download = 'ai-career-coach-feedback.txt'; anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  const card = (title, items) => <article className="panel report-card"><h3>{title}</h3><ul>{items.map((item, i) => <li key={i}>{item}</li>)}</ul></article>;
  return <div id={id}>{coverage && <div className={`assessment-coverage ${assessment?.partial ? "partial" : ""}`}><strong>{coverage}</strong><p>{assessment?.limitations || "Older reports may not indicate whether the interview ended early."}</p></div>}{record.demo && <div className="alert demo-badge">DEMO REPORT · Illustrative feedback from simple rules, not an AI assessment.</div>}<div className="report-hero"><div className="score"><strong>{Math.round(r.score)}</strong><small>OUT OF 100</small></div><div><h2>Your next step, a little clearer.</h2><p>{r.summary}</p></div></div><article className="panel score-explanation"><h3>Why this score?</h3><p>{r.score_explanation || "This older report did not include a separate score explanation. Its summary and feedback are preserved below."}</p><small>{scoreNote}</small></article><div className="report-grid">{card('✧ What’s working', r.strengths)}{card('↗ Room to grow', r.improvements)}</div>{card('Your next steps', r.next_steps)}<details className="panel" hidden={!record.context?.messages?.length}><summary>Interview questions and your answers</summary>{record.context?.messages?.map((message, i) => <div key={i}><strong>{message.role === "assistant" ? "Interviewer" : "You"}</strong><p style={{ whiteSpace: "pre-wrap" }}>{message.content}</p></div>)}</details><div className="report-actions"><Action onClick={restart}>{record.type === 'CV review' ? 'Edit & review again ↗' : 'Practice again ↗'}</Action><button className="btn secondary" onClick={download}>Download feedback ↓</button></div></div>;
}

// PSEUDOCODE: INTERVIEW UI STATE
// RESTORE role, conversation and answer draft from shared workspace state.
// APPLY profile defaults or a targeted-practice preset.
// RENDER setup, the current conversation or completed feedback.
function Interview({ demo, busy, run, notify, onComplete, record, setRecord, preset, profile, store, active }) {
  const [role, setRole] = useWorkspaceState(store, 'interview.role', '');
  const [description, setDescription] = useWorkspaceState(store, 'interview.description', '');
  const [total, setTotal] = useWorkspaceState(store, 'interview.total', 5);
  const [session, setSession] = useWorkspaceState(store, 'interview.session', null);
  const [answer, setAnswer] = useWorkspaceState(store, 'interview.answer', '');
  const answerRef = useRef(null);
  const [dictating, setDictating] = useState(false);
  const [confirmLeave, setConfirmLeave] = useState(false);
  useEffect(() => { if (!role && profile.role) setRole(profile.role); }, [profile.role]);
  useEffect(() => { if (preset) { setRole(preset.role); setDescription(preset.description || ''); setTotal(preset.focus ? 3 : 5); setSession(null); setAnswer(''); } }, [preset]);
  useEffect(() => { if (session && !busy && !record) answerRef.current?.focus(); }, [session, busy, record]);
  // PSEUDOCODE: COMPLETE INTERVIEW
  // BUILD a report record with answered transcript and practice context.
  // CLEAR the active conversation/answer and add the report to history.
  async function complete(result, candidate) {
    const item = { type: 'Mock interview', role: candidate.role, report: result.report, assessment: result.assessment, demo: result.demo, date: new Date(), context: { total: candidate.total, focus: candidate.focus || '', description: candidate.description, messages: candidate.messages.filter((message, index) => message.role === 'user' || candidate.messages[index + 1]?.role === 'user') } };
    setSession(null); setAnswer(''); if (await onComplete(item) !== false) setRecord(item);
  }
  // PSEUDOCODE: START INTERVIEW
  // BUILD the role/context payload with an empty transcript.
  // REQUEST the first question and save the new conversation.
  function start(event) {
    event.preventDefault();
    run(async () => {
      const candidate = { role: role.trim(), description: description.trim(), total, demo, messages: [], focus: preset?.focus || '', goal: profile.goal };
      const result = await api('/api/interview', candidate);
      setSession({ ...candidate, messages: [{ role: 'assistant', content: result.question }] }); setRecord(null);
    });
  }
  // PSEUDOCODE: SEND ANSWER
  // REQUIRE stopped dictation and a nonempty answer.
  // APPEND the user answer and request the next server response.
  // IF feedback arrives, complete the session.
  // OTHERWISE append the next question and clear the answer draft.
  function send(event) {
    event.preventDefault();
    if (dictating) return notify('Stop dictation and review your answer before sending.');
    if (!answer.trim()) return notify('Add an answer before continuing.');
    run(async () => {
      const candidate = { ...session, messages: [...session.messages, { role: 'user', content: answer.trim() }] };
      const result = await api('/api/interview', candidate);
      if (result.report) await complete(result, candidate);
      else { setSession({ ...candidate, messages: [...candidate.messages, { role: 'assistant', content: result.question }] }); setAnswer(''); }
    });
  }
  // PSEUDOCODE: EARLY FINISH
  // REQUIRE stopped dictation and no unsent answer.
  // REMOVE the unanswered final question and require an answered pair.
  // REQUEST feedback for the answered portion of the conversation.
  function finish() {
    if (dictating) return notify('Stop dictation before finishing.');
    if (answer.trim()) return notify('Send your current answer first so it is included in feedback.');
    const messages = session.messages.slice(0, -1);
    if (!messages.length) return notify('Answer at least one question first.');
    run(async () => complete(await api('/api/interview', { ...session, messages, finish: true }), { ...session, messages }));
  }
  // PSEUDOCODE: RETURN TO INTERVIEW SETUP
  // CLEAR the unfinished conversation and answer after confirmation.
  // KEEP role and job description so a fresh interview is easy to start.
  function returnToSetup() {
    setSession(null); setAnswer(''); setRecord(null); setConfirmLeave(false);
    notify('Returned to interview setup. The unfinished conversation was discarded.');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
  const answered = session?.messages.filter(item => item.role === 'user').length || 0;
  return <section id="interview" className="page"><CharacterGuide room="interview" /><div className="eyebrow">PRACTICE WITH PURPOSE</div><h1>Meet your interview alter ego.</h1><p className="subtitle">A safe place to find your words, before the real conversation.</p>
    {preset?.focus && <div className="practice-focus"><strong>Targeted practice</strong><p>{preset.focus}</p><small>Give a specific example, explain your contribution, and show the outcome. Your final feedback will assess this focus.</small></div>}{record ? <Report id="interview-report" record={record} restart={() => setRecord(null)} /> : session ? <div id="interview-session"><button type="button" className="btn secondary mb-3" disabled={busy} onClick={() => setConfirmLeave(true)}>Back to interview setup</button>{confirmLeave && <div className="alert alert-warning" role="alert"><p>Return to setup? This discards the unfinished conversation and unsent answer. Your role, job description and completed reports will stay saved.</p><div className="d-flex flex-wrap gap-2"><button type="button" className="btn secondary" disabled={busy} onClick={returnToSetup}>Discard &amp; return to setup</button><button type="button" className="btn secondary" onClick={() => setConfirmLeave(false)}>Keep practicing</button></div></div>}<div className="session-heading"><div><span className="eyebrow">YOUR PRACTICE SESSION</span><h2 id="session-role">{session.role}</h2></div><span id="question-progress" className="pill pale">Question {Math.min(answered + 1, session.total)} of {session.total}{session.demo ? ' · Demo' : ''}</span></div><div className="progress progress-track" role="progressbar" aria-label="Interview progress" aria-valuenow={answered} aria-valuemin={0} aria-valuemax={session.total}><div id="progress-fill" className="progress-bar" style={{ width: `${answered / session.total * 100}%` }} /></div><div className="panel chat-panel"><div id="messages" aria-live="polite" aria-label="Interview conversation">{session.messages.map((message, i) => <div key={i} className={`message ${message.role}`}><span className="message-icon">{message.role === 'assistant' ? <DojoIcon name="mentor" /> : <DojoIcon name="trainee" />}</span><div className="message-body"><small>{message.role === 'assistant' ? 'YOUR INTERVIEWER' : 'YOU'}</small><p>{message.content}</p></div></div>)}</div><form id="answer-form" onSubmit={send} aria-busy={busy}><label htmlFor="answer">Your answer</label><textarea className="form-control" ref={answerRef} readOnly={dictating || busy} id="answer" rows={4} maxLength={6000} required value={answer} onChange={e => setAnswer(e.target.value)} onKeyDown={e => { if (e.ctrlKey && e.key === 'Enter' && !busy) { e.preventDefault(); e.currentTarget.form.requestSubmit(); } }} placeholder="Take your time. A specific example is a great place to start…" /><Dictation active={active && !!session && !record} disabled={busy} onActive={setDictating} append={text => setAnswer(previous => `${previous}${previous && !/\s$/.test(previous) ? " " : ""}${text.trim()}`.slice(0, 6000))} /><div className="answer-actions"><button className="btn text-button" type="button" id="finish" disabled={busy || dictating} onClick={finish}>Finish & get feedback</button><Action busy={busy} disabled={busy || dictating} id="send" type="submit">{busy ? 'Thinking…' : 'Send answer ↑'}</Action></div><small>Ctrl + Enter to send</small></form></div></div> : <div id="interview-setup" className="form-layout"><form id="setup-form" className="panel" onSubmit={start} aria-busy={busy}><div className="panel-heading"><span className="tool-icon peach"><DojoIcon name="interview" /></span><div><h2>Make it your interview</h2><p>Tell us a little about the opportunity.</p></div></div><Field id="interview-role" label="Target role"><input className="form-control" id="interview-role" required minLength={2} maxLength={160} value={role} onChange={e => setRole(e.target.value)} placeholder="e.g. Frontend Developer" /></Field><Field id="interview-description" label="Job description" optional><textarea className="form-control" id="interview-description" rows={5} maxLength={12000} value={description} onChange={e => setDescription(e.target.value)} placeholder="Paste the job description for a more tailored conversation…" /></Field><label htmlFor="question-count">Session length</label><select className="form-select" id="question-count" value={total} onChange={e => setTotal(Number(e.target.value))}><option value={3}>Quick warm-up · 3 questions</option><option value={5}>Focused practice · 5 questions</option><option value={8}>Deep dive · 8 questions</option></select><Action busy={busy} type="submit">{busy ? 'Preparing your interview…' : 'Start my interview ↗'}</Action></form><Tip /></div>}
  </section>;
}

// PSEUDOCODE: CV REVIEW UI
// KEEP editable CV/role/description in shared workspace state.
// UPLOAD a document to extract text, or accept pasted text.
// REQUEST review feedback and store the completed record with its CV context.
function CV({ demo, busy, run, notify, onComplete, record, setRecord, store }) {
  const [role, setRole] = useWorkspaceState(store, 'cv.role', '');
  const [description, setDescription] = useWorkspaceState(store, 'cv.description', '');
  const [cv, setCV] = useWorkspaceState(store, 'cv.cv', '');
  const [filename, setFilename] = useWorkspaceState(store, 'cv.filename', '');
  const [extracting, setExtracting] = useState(false);
  useEffect(() => { if (record) { setRole(record.role); setDescription(record.context?.description || ''); setCV(record.context?.cv || ''); } }, [record]);
  function upload(event) {
    const input = event.target, file = input.files[0];
    if (!file) return;
    if (file.size > 4 * 1024 * 1024) { input.value = ''; return notify('Choose a file of 4 MB or less.'); }
    run(async () => {
      setExtracting(true);
      try { const form = new FormData(); form.append('file', file); const result = await api('/api/extract', form); setCV(result.text); setFilename(file.name); }
      finally { input.value = ''; setExtracting(false); }
    });
  }
  function review(event) {
    event.preventDefault();
    run(async () => {
      const result = await api('/api/review', { role: role.trim(), description: description.trim(), cv: cv.trim(), demo });
      const item = { type: 'CV review', role: role.trim(), report: result.report, demo: result.demo, date: new Date(), context: { cv: cv.trim(), description: description.trim() } };
      if (await onComplete(item) !== false) setRecord(item);
    });
  }
  return <section id="cv" className="page"><CharacterGuide room="cv" /><div className="eyebrow">PUT YOUR BEST STORY FORWARD</div><h1>Time for a CV glow-up.</h1><p className="subtitle">Make your experience work harder for your next opportunity.</p>{record ? <Report id="cv-report" record={record} restart={() => setRecord(null)} /> : <div id="cv-input" className="form-layout"><form id="cv-form" className="panel" onSubmit={review} aria-busy={busy}><div className="panel-heading"><span className="tool-icon lilac"><DojoIcon name="cv" /></span><div><h2>A fresh perspective on your CV</h2><p>Share your CV and the role you’re aiming for.</p></div></div><Field id="cv-role" label="Target role"><input className="form-control" id="cv-role" required minLength={2} maxLength={160} value={role} onChange={e => setRole(e.target.value)} placeholder="e.g. Product Manager" /></Field><Field id="cv-description" label="Job description" optional><textarea className="form-control" id="cv-description" rows={3} maxLength={12000} value={description} onChange={e => setDescription(e.target.value)} placeholder="What is the company looking for?" /></Field><label className="upload-zone" htmlFor="cv-file"><span className="upload-icon"><DojoIcon name="upload" /></span><strong id="file-label">{extracting ? 'Reading your CV…' : filename || 'Choose a CV to upload'}</strong><small>PDF, DOCX or TXT · up to 4 MB</small><input type="file" id="cv-file" accept=".pdf,.docx,.txt" disabled={busy} onChange={upload} /></label><div className="or-line"><span />or paste your text<span /></div><label htmlFor="cv-text">CV contents <span>*</span></label><textarea className="form-control" id="cv-text" rows={9} minLength={80} maxLength={30000} required value={cv} onChange={e => setCV(e.target.value)} placeholder="Paste your experience, education, skills and achievements here…" /><small id="cv-count">{cv.length.toLocaleString()} / 30,000 characters</small><p className="privacy-copy">Live reviews send your CV text to OpenAI. Remove personal details you don’t want to share. Files are processed in memory and are not saved.</p><Action busy={busy} type="submit">{busy ? 'Reviewing your story…' : 'Review my CV ↗'}</Action></form><Tip cv /></div>}</section>;
}


function sameSession(first, second) {
  if (!first || !second) return false;
  if (first.id && second.id) return first.id === second.id;
  return first.type === second.type && first.role === second.role && new Date(first.date).getTime() === new Date(second.date).getTime() && JSON.stringify(first.report) === JSON.stringify(second.report);
}

// PSEUDOCODE: INDIVIDUAL REPORT CONTROLS
// RENDER each saved session with View feedback and Delete.
// REQUIRE an inline confirmation before removing the selected report.
// RENDER this list only in My journey > History & feedback.
function SavedSessions({ completed, navigate, view, remove, busy }) {
  const [pendingDelete, setPendingDelete] = useState(null);
  return <div>{completed.length ? completed.map((record, i) => <article key={i} className="panel history-row"><div><h3>{record.role}</h3><p>{record.type} · {new Date(record.date).toLocaleString()} · {record.demo ? 'Demo' : 'Live AI'}</p></div><div className="history-score">{Math.round(record.report.score)}<small> / 100</small></div><div className="d-flex flex-wrap gap-2"><button className="btn secondary" onClick={() => view(record)}>View feedback</button>{pendingDelete === record ? <div role="group" aria-label="Confirm session deletion"><p>Delete this {record.type.toLowerCase()} for {record.role}?</p><button className="btn btn-danger me-2" disabled={busy} onClick={() => { remove(record); setPendingDelete(null); }}>Delete this session</button><button className="btn secondary" onClick={() => setPendingDelete(null)}>Cancel</button></div> : <button className="btn secondary" disabled={busy} onClick={() => setPendingDelete(record)}>Delete</button>}</div></article>) : <div className="panel empty-state"><span className="spark">✦</span><h2>Your first step is waiting.</h2><p>Complete an interview or a CV review to see your feedback here.</p><Action onClick={() => navigate('interview')}>Start practicing ↗</Action></div>}</div>;
}

// PSEUDOCODE: MY JOURNEY
// GROUP report history, goals/stories and data settings behind three tabs.
// KEEP the story editor mounted so switching tabs preserves an unfinished draft.
function Journey({ tab, setTab, store, completed, navigate, view, remove, busy, children }) {
  const tabs = { history: 'History & feedback', stories: 'Goals & stories', settings: 'Data settings' };
  function tabKey(event, key) {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const keys = Object.keys(tabs), index = keys.indexOf(key);
    const next = event.key === 'Home' ? keys[0] : event.key === 'End' ? keys.at(-1) : keys[(index + (event.key === 'ArrowRight' ? 1 : -1) + keys.length) % keys.length];
    setTab(next); document.getElementById(`journey-tab-${next}`)?.focus();
  }
  return <section id="journey" className="page journey-page"><div className="eyebrow">YOUR EXPERIENCE. YOUR NEXT CHAPTER.</div><h1>My journey.</h1><p className="subtitle">Your feedback, your stories, and your next steps. All in one place.</p>
    <CharacterGuide room="stories" />
    <div className="journey-tabs" role="tablist" aria-label="My journey sections">{Object.entries(tabs).map(([key, label]) => <button type="button" role="tab" key={key} id={`journey-tab-${key}`} aria-controls={`journey-${key}`} aria-selected={tab === key} tabIndex={tab === key ? 0 : -1} onKeyDown={event => tabKey(event, key)} onClick={() => setTab(key)}><MemoryIcon name={key === 'history' ? 'progress' : key === 'stories' ? 'story' : 'shield'} />{label}</button>)}</div>
    <div id="journey-history" role="tabpanel" aria-labelledby="journey-tab-history" hidden={tab !== 'history'}><div className="journey-history-heading"><div><h2>History &amp; feedback</h2><p>Reopen completed interviews and CV reviews, or delete individual reports.</p></div><button className="journey-settings-link" onClick={() => setTab('settings')}>Device saving {store.enabled ? 'on' : 'off'} <span aria-hidden="true">&#8594;</span></button></div>{store.error && <p role="alert">{store.error}</p>}<div id="progress-list"><SavedSessions completed={completed} navigate={navigate} view={view} remove={remove} busy={busy} /></div><p className="journey-footnote">Up to 50 interview and CV reports. Career Lab keeps its own results in the Lab.</p></div>
    {children}
  </section>;
}

// PSEUDOCODE: APPLICATION COORDINATION
// CREATE shared memory, navigation, demo mode and request state.
// CHECK AI configuration periodically and respect the user mode choice.
// PASS shared state and callbacks into each feature component.
function App() {
  const [page, setPage] = useState('overview');
  const [journeyTab, setJourneyTab] = useState('history');
  const [busy, setBusy] = useState(false);
  const busyRef = useRef(false);
  const [notice, setNotice] = useState('');
  const [demo, setDemo] = useState(true);
  const [connection, setConnection] = useState('Checking AI connection…');
  const [ready, setReady] = useState(false);
  const modeChosen = useRef(false);
  const store = useCareerMemory();
  const completed = store.memory.sessions;
  const [interviewReport, setInterviewReport] = useState(null);
  const [cvReport, setCVReport] = useState(null);
  const [interviewPreset, setInterviewPreset] = useState(null);
  useEffect(() => { if (store.resetToken) { setInterviewReport(null); setCVReport(null); setInterviewPreset(null); } }, [store.resetToken]);
  useEffect(() => {
    let active = true;
    async function refreshStatus() {
      try {
        const response = await fetch('/api/status', { cache: 'no-store' });
        if (!response.ok) throw new Error();
        const data = await response.json();
        if (!active) return;
        setReady(data.ai_ready);
        if (!modeChosen.current) setDemo(!data.ai_ready);
        setConnection(data.ai_ready ? 'Live AI configured' : 'Demo available - Live AI needs a server API key');
      } catch { if (active) setConnection('Could not connect to the server'); }
    }
    refreshStatus();
    const timer = setInterval(refreshStatus, 10000);
    window.addEventListener('focus', refreshStatus);
    return () => { active = false; clearInterval(timer); window.removeEventListener('focus', refreshStatus); };
  }, []);

  function navigate(target) {
    if (busyRef.current) return setNotice('Please wait for the current request to finish.');
    if (target === 'progress') { setJourneyTab('history'); target = 'journey'; }
    if (target === 'memory') { setJourneyTab('stories'); target = 'journey'; }
    if (target === 'settings') { setJourneyTab('settings'); target = 'journey'; }
    setPage(target); window.scrollTo({ top: 0, behavior: 'smooth' });
  }
  // PSEUDOCODE: REQUEST LIFECYCLE
  // BLOCK overlapping app requests and show loading state.
  // RUN the requested operation, show readable errors and always clear loading.
  async function run(fn) {
    if (busyRef.current) return;
    busyRef.current = true; setBusy(true); setNotice('');
    try { await fn(); } catch (error) { setNotice(error.message || 'Connection lost. Please retry.'); }
    finally { busyRef.current = false; setBusy(false); }
  }
  // PSEUDOCODE: SAVE COMPLETED REPORT
  // PREPEND the new report and keep the latest 50 interview/CV sessions.
  async function onComplete(record) { const saved = { ...record, id: record.id || crypto.randomUUID() }; const written = await store.setMemory(m => ({ ...m, sessions: [saved, ...m.sessions].slice(0, 50) })); if (written !== false) window.scrollTo({ top: 0, behavior: 'smooth' }); return written; }
  // PSEUDOCODE: DELETE ONE REPORT
  // REMOVE only the selected record from shared sessions.
  // CLEAR its open report view if necessary and show confirmation.
  // LEAVE other reports, stories and independent drafts unchanged.
  function deleteSession(record) {
    if (busyRef.current) return;
    store.setMemory(memory => ({ ...memory, sessions: memory.sessions.filter(item => !sameSession(item, record)) }));
    if (sameSession(interviewReport, record)) setInterviewReport(null);
    if (sameSession(cvReport, record)) setCVReport(null);
    setNotice('Session deleted. Your other saved sessions are unchanged.');
  }
  function view(record) { if (record.type === 'CV review') { setCVReport(record); navigate('cv'); } else { setInterviewReport(record); navigate('interview'); } }
  return <div className="dojo-theme"><a className="skip-link" href="#main-content">Skip to main content</a><aside className="sidebar"><a className="brand" href="/" aria-label="AI Career Coach home"><span className="brand-icon"><DojoMark /></span><span className="brand-name">Career Dojo<small>AI CAREER COACH</small></span></a><div className="workspace-label">YOUR WORKSPACE</div><nav aria-label="Main navigation">{Object.entries(pages).map(([key, label]) => <button key={key} className={`nav ${page === key ? 'active' : ''}`} data-page={key} aria-current={page === key ? 'page' : undefined} onClick={() => navigate(key)}><span><DojoIcon name={key} /></span>{label}</button>)}</nav><button type="button" className={`sidebar-about ${page === "about" ? "active" : ""}`} aria-current={page === "about" ? "page" : undefined} onClick={() => navigate("about")}><MemoryIcon name="about" /> About this app</button><div className="sidebar-note"><span className="spark">&#10022;</span><strong>Tiny steps.<br />Big plot twists.</strong><p>Your future self is already cheering you on.</p></div><div className="profile"><div><strong>Your career space</strong><small>Make room for what’s next</small></div></div></aside><div className="shell"><header><span id="breadcrumb">Workspace / {page === 'about' ? 'About' : pages[page]}</span><div className="header-right"><span className="private-dot" aria-hidden="true" /><button className="saving-status" onClick={() => navigate("settings")}>Device saving {store.enabled ? "on" : "off"}</button></div></header><main id="main-content" tabIndex={-1}><div className="mode-bar"><span id="connection">{connection}</span><label className="mode-toggle"><input className="form-check-input" type="checkbox" id="demo" checked={demo} disabled={busy} onChange={e => { modeChosen.current = true; setDemo(e.target.checked); if (!e.target.checked && !ready) setNotice('Live AI needs OPENAI_API_KEY configured on the server. Demo mode works without a key.'); }} /> Use demo mode</label></div><div className="data-use-note" id="data-use-note"><p>{store.enabled ? "Device saving is on: CV text, interview answers and results stay in this browser." : "Device saving is off: your work is kept only for this visit."} Live AI sends submitted content to OpenAI. Demo results use illustrative rules.</p><button onClick={() => navigate("settings")}>Manage data</button></div><div hidden={page !== 'overview'}><DojoOverview navigate={navigate} store={store} /></div><div hidden={page !== 'interview'}><Interview active={page === "interview"} demo={demo} busy={busy} run={run} notify={setNotice} onComplete={onComplete} record={interviewReport} setRecord={setInterviewReport} preset={interviewPreset} profile={store.memory.profile} store={store} /></div><div hidden={page !== 'cv'}><CV demo={demo} busy={busy} run={run} notify={setNotice} onComplete={onComplete} record={cvReport} setRecord={setCVReport} store={store} /></div><div hidden={page !== 'lab'}><CareerLab store={store} demo={demo} busy={busy} run={run} api={api} notify={setNotice} completed={completed} onPractice={preset => { setInterviewPreset(preset); setInterviewReport(null); navigate('interview'); }} /></div><div hidden={page !== 'journey'}><Journey tab={journeyTab} setTab={setJourneyTab} store={store} completed={completed} navigate={navigate} view={view} remove={deleteSession} busy={busy}><CareerMemory view={journeyTab} store={store} demo={demo} busy={busy} run={run} api={api} notify={setNotice} practice={preset => { setInterviewPreset({ ...preset, key: Date.now() }); setInterviewReport(null); navigate('interview'); }} onClear={() => { store.clear(); setInterviewReport(null); setCVReport(null); setInterviewPreset(null); setNotice('Saved app data deleted.'); }} /></Journey></div><div hidden={page !== 'about'}><About navigate={navigate} savingEnabled={store.enabled} /></div>{notice && <div id="notice" className="alert alert-warning" role="alert"><span id="notice-text">{notice}</span><button id="dismiss-notice" aria-label="Dismiss message" onClick={() => setNotice('')}>×</button></div>}<footer><span className="footer-brand">AI Career Coach.</span><span>Big dreams. Good vibes. Real practice.</span><small>Practice feedback, not a hiring prediction.</small></footer></main></div></div>;
}

createRoot(document.getElementById('root')).render(<App />);
