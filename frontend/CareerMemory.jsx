import { useState } from 'react';
import './memory.css';
import { MemoryIcon } from './MemoryArt.jsx';

const blank = () => ({ title: '', skill: '', source: '', situation: '', task: '', action: '', result: '' });
const steps = ['situation', 'task', 'action', 'result'];

// PSEUDOCODE: CAREER MEMORY UI
// EDIT profile goals and maintain reviewed STAR evidence stories.
// SHOW focused practice suggestions in Goals & stories.
// KEEP saving preferences, export and full deletion in Data settings.
export default function CareerMemory({ store, demo, busy, run, api, notify, practice, onClear, view }) {
  const { memory, setMemory, enabled, setEnabled, error } = store;
  const [draft, setDraft] = useState(blank);
  const [reviewed, setReviewed] = useState(false);
  const [confirmClear, setConfirmClear] = useState(false);
  function edit(key, value) { setDraft(d => ({ ...d, [key]: value })); setReviewed(false); }
  // PSEUDOCODE: SAVE A STORY
  // REQUIRE user confirmation that the story reflects real experience.
  // ASSIGN an ID, replace an edited story or add a new one, and keep 100.
  // RESET the story editor after saving.
  function save(event) {
    event.preventDefault();
    if (!reviewed) return notify('Check that this story describes your real experience before saving.');
    const story = { ...draft, id: draft.id || crypto.randomUUID() };
    setMemory(m => ({ ...m, stories: [story, ...m.stories.filter(s => s.id !== story.id)].slice(0, 100) }));
    setDraft(blank()); setReviewed(false); notify('Evidence story saved.');
  }
  // PSEUDOCODE: REQUEST STAR DRAFT
  // REQUIRE a skill and enough source experience.
  // REQUEST demo/live structuring, populate the editor and require review again.
  function structure() {
    if (draft.source.trim().length < 40 || draft.skill.trim().length < 2) return notify('Add a skill and at least 40 characters of real experience first.');
    run(async () => {
      const result = await api('/api/evidence', { source: draft.source, skill: draft.skill, demo });
      setDraft(d => result.fallback ? { ...d, situation: d.situation || result.story.situation } : { ...d, ...result.story }); setReviewed(false);
      notify(result.recovery_notice || (result.demo ? 'Demo template created. Replace the prompts with your own facts.' : 'Draft structured from your source. Review it and fill any missing evidence before saving.'));
    });
  }
  // PSEUDOCODE: EXPORT DEVICE MEMORY
  // SERIALIZE the shared memory as versioned JSON.
  // CREATE a temporary download URL and release it after starting the download.
  function exportMemory() {
    const url = URL.createObjectURL(new Blob([JSON.stringify({ version: 1, memory }, null, 2)], { type: 'application/json' }));
    const a = document.createElement('a'); a.href = url; a.download = 'career-memory.json'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  const latest = memory.sessions.find(s => s.type === 'Mock interview' && s.demo === demo);
  const previous = latest && memory.sessions.filter(s => s.type === latest.type && s.role.toLowerCase() === latest.role.toLowerCase() && s.demo === latest.demo).slice(0, 5).reverse();
  return <section className="career-memory">
    <div id="journey-settings" role="tabpanel" aria-labelledby="journey-tab-settings" hidden={view !== 'settings'}>
    <div className="panel memory-controls"><div className="memory-storage-heading"><span className="memory-bubble mint"><MemoryIcon name="shield" /></span><div><span className="memory-kicker">YOUR SPACE, YOUR CHOICE</span><h2>Data settings</h2></div></div><label><input type="checkbox" checked={enabled} onChange={e => setEnabled(e.target.checked)} /> Remember on this device</label><p>{enabled ? 'Goals, evidence stories, CV text, interview drafts and transcripts, up to 50 feedback reports, and up to 50 Career Lab results are saved in this browser across visits.' : 'Memory lasts for this visit. Enable saving to keep it after closing or refreshing.'} This device has no account sign-in or cross-device sync. Anyone using this browser profile can access saved information.</p><p>Turning saving off removes the stored copy and keeps the current visit. “Delete all saved data” also clears this visit. Live coaching sends submitted content to OpenAI.</p><div className="memory-actions"><button className="btn secondary" onClick={exportMemory}>Export my data</button><button className="btn secondary" disabled={busy} onClick={() => setConfirmClear(true)}>Delete all saved data</button></div>{confirmClear && <div className="alert alert-warning" role="alert">Delete all saved goals, stories, drafts, transcripts, and results from this app on this browser?<div className="memory-actions"><button className="btn secondary" onClick={() => { onClear(); setDraft(blank()); setReviewed(false); setConfirmClear(false); }}>Delete all</button><button className="btn secondary" onClick={() => setConfirmClear(false)}>Cancel</button></div></div>}{error && <p role="alert">{error}</p>}</div>
    </div>
    <div id="journey-stories" role="tabpanel" aria-labelledby="journey-tab-stories" hidden={view !== 'stories'}>
    <div className="journey-history-heading"><div><h2>Goals &amp; stories</h2><p>Set your direction, collect real examples, and choose a focus for your next practice.</p></div></div>
    <div className="lab-layout"><div><article className="panel lab-form"><div className="memory-card-heading"><span className="memory-bubble peach"><MemoryIcon name="target" /></span><div><span className="memory-kicker">01 / LOOK AHEAD</span><h2>Your direction</h2></div></div><label htmlFor="memory-role">Target role</label><input id="memory-role" className="form-control" maxLength={160} value={memory.profile.role} onChange={e => { const value = e.target.value; setMemory(m => ({ ...m, profile: { ...m.profile, role: value } }), { optimistic: true }); }} /><label htmlFor="memory-goal">Career goal</label><textarea id="memory-goal" className="form-control" rows={3} maxLength={2000} value={memory.profile.goal} onChange={e => { const value = e.target.value; setMemory(m => ({ ...m, profile: { ...m.profile, goal: value } }), { optimistic: true }); }} placeholder="What would you like to achieve?" /></article>
    <article className="panel lab-form"><div className="memory-card-heading"><span className="memory-bubble lilac"><MemoryIcon name="practice" /></span><div><span className="memory-kicker">02 / KEEP GROWING</span><h2>Your next practice</h2></div></div><p>{demo ? 'Demo practice uses illustrative feedback.' : 'Live practice uses feedback from your latest live interview.'} Choose a focus to start a three-question exercise.</p>{latest ? <><p><strong>{latest.role}</strong></p>{latest.report.improvements.map((focus, i) => <button key={i} className="btn secondary memory-focus" disabled={busy} onClick={() => practice({ role: latest.role, description: '', focus, goal: memory.profile.goal })}>{focus}<span>Practice this →</span></button>)}<p>Recent scores for this role and mode. Scores are coaching guidance, not a standardized measurement.</p><ol className="memory-scores">{previous.map((s, i) => <li key={i}>{new Date(s.date).toLocaleDateString()}: <strong>{Math.round(s.report.score)}/100</strong>{s.context?.focus && <small>Focus: {s.context.focus}</small>}</li>)}</ol></> : <p>Complete an interview in the current mode to get targeted practice suggestions.</p>}</article></div>
    <form className="panel lab-form" onSubmit={save}><div className="memory-card-heading"><span className="memory-bubble butter"><MemoryIcon name="story" /></span><div><span className="memory-kicker">03 / COLLECT THE GOOD STUFF</span><h2>{draft.id ? 'Edit your evidence story' : 'Build an evidence story'}</h2></div></div><p>Turn a real experience into a Situation, Task, Action, Result story. You approve every draft.</p><label htmlFor="story-title">Story title</label><input id="story-title" className="form-control" required maxLength={160} value={draft.title} onChange={e => edit('title', e.target.value)} /><label htmlFor="story-skill">Skill demonstrated</label><input id="story-skill" className="form-control" required minLength={2} maxLength={160} value={draft.skill} onChange={e => edit('skill', e.target.value)} placeholder="For example: teamwork or problem solving" /><label htmlFor="story-source">Your original experience</label><textarea id="story-source" className="form-control" rows={4} maxLength={12000} value={draft.source} onChange={e => edit('source', e.target.value)} placeholder="Describe what actually happened. Include your actions and verified outcomes." /><button className="btn secondary" type="button" disabled={busy} onClick={structure}>{busy ? 'Working…' : demo ? 'Create demo template' : 'Structure with AI'}</button>{steps.map(k => <div key={k} className={`memory-star-step step-${k}`}><label htmlFor={`story-${k}`}><span className="memory-step-letter" aria-hidden="true">{k[0].toUpperCase()}</span>{k[0].toUpperCase() + k.slice(1)}</label><textarea id={`story-${k}`} className="form-control" rows={2} required maxLength={12000} value={draft[k]} onChange={e => edit(k, e.target.value)} /></div>)}<label className="memory-check"><input type="checkbox" required checked={reviewed} onChange={e => setReviewed(e.target.checked)} /> I reviewed this story. Its claims reflect my real experience.</label><div className="memory-actions"><button className="btn primary" disabled={busy}>Save story</button>{draft.id && <button type="button" className="btn secondary" onClick={() => { setDraft(blank()); setReviewed(false); }}>Cancel edit</button>}</div></form></div>
    <div className="memory-bank-heading"><span className="memory-bubble mint"><MemoryIcon name="brain" /></span><div><span className="memory-kicker">YOU DID THAT</span><h2>Your evidence bank <small>({memory.stories.length})</small></h2></div></div>{!memory.stories.length && <div className="memory-empty"><span className="memory-empty-art" aria-hidden="true"><MemoryIcon name="story" /><span>+</span></span><h3>Your first story is waiting.</h3><p>A tricky project. A teammate you helped. A small win.<br />Add one real example above and watch your collection grow.</p></div>}<div className="memory-bank">{memory.stories.map(s => <article className="panel lab-form memory-story-card" key={s.id}><span className="memory-story-mark"><MemoryIcon name="story" /></span><span className="pill pale">{s.skill}</span><h3>{s.title}</h3>{steps.map(k => <p key={k}><strong>{k[0].toUpperCase() + k.slice(1)}: </strong>{s[k]}</p>)}<div className="memory-actions"><button className="btn primary" disabled={busy || memory.profile.role.trim().length < 2} onClick={() => practice({ role: memory.profile.role, description: '', focus: `Practice explaining ${s.skill} using this real example. Situation: ${s.situation}; Task: ${s.task}; Action: ${s.action}; Result: ${s.result}`.slice(0, 1200), goal: memory.profile.goal })}>Practice story</button><button className="btn secondary" disabled={busy} onClick={() => { setDraft({ ...s }); setReviewed(false); document.getElementById('story-title')?.focus(); }}>Edit</button><button className="btn secondary" disabled={busy} onClick={() => setMemory(m => ({ ...m, stories: m.stories.filter(x => x.id !== s.id) }))}>Remove</button></div></article>)}</div><p>Set a target role to practice a saved story. Keep an exported backup of anything important.</p>
    </div>
  </section>;
}
