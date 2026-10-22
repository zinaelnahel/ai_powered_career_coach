import { plainProse, roadmapGaps, companyPracticeDescription } from './textQuality.js';
import CharacterGuide from './CharacterGuide.jsx';
import { useWorkspaceState } from './memory.js';
import LabArt from './LabArt.jsx';
import { MemoryIcon } from './MemoryArt.jsx';

const tools = {
  jobs: { label: 'Find jobs', heading: 'Your next opportunity is out there.', intro: 'Find relevant offers, then bring a role straight into your job-fit check.', action: 'Find opportunities ↗', endpoint: 'jobs' },
  fit: { label: 'Job fit', heading: 'Find your strengths. Spot the gaps.', intro: 'Compare your CV with a specific job description and see where your evidence shines.', action: 'Check my fit ↗', endpoint: 'fit' },
  roadmap: { label: 'Learning plan', heading: 'Big goals. A doable game plan.', intro: 'Turn your skill gaps and interview feedback into weekly, practical milestones.', action: 'Build my roadmap ↗', endpoint: 'roadmap' },
  company: { label: 'Company prep', heading: 'Walk in knowing the company.', intro: 'Research company values and prepare thoughtful, role-specific examples.', action: 'Research & prepare ↗', endpoint: 'company-prep' },
};
const safeLink = value => typeof value === 'string' && value.startsWith('https://') ? value : undefined;

function Sources({ sources, title = 'Research sources' }) {
  if (!sources?.length) return null;
  return <aside className="lab-sources"><strong>{title}</strong><ul>{sources.map(source => <li key={source.url}><a href={safeLink(source.url)} target="_blank" rel="noopener noreferrer">{source.title} ↗</a></li>)}</ul></aside>;
}
function Score({ value, label }) {
  return <div className="lab-score"><strong>{Math.round(value)}<small>/100</small></strong><span>{label}</span></div>;
}
function Bullets({ items }) { return <ul className="lab-list">{items.map((item, i) => <li key={i}>{item}</li>)}</ul>; }

// PSEUDOCODE: CAREER LAB UI
// RESTORE tool forms, current results, history and milestone state.
// IGNORE removed tool tabs/history entries when rendering.
// RENDER the selected tool and allow reopening older supported results.
export default function CareerLab({ demo, busy, run, api, notify, completed, onPractice, store }) {
  const [savedTab, setTab] = useWorkspaceState(store, 'lab.tab', 'jobs');
  const tab = Object.hasOwn(tools, savedTab) ? savedTab : 'jobs';
  const [role, setRole] = useWorkspaceState(store, 'lab.role', '');
  const [location, setLocation] = useWorkspaceState(store, 'lab.location', '');
  const [company, setCompany] = useWorkspaceState(store, 'lab.company', '');
  const [cv, setCV] = useWorkspaceState(store, 'lab.cv', '');
  const [description, setDescription] = useWorkspaceState(store, 'lab.description', '');
  const [offerContext, setOfferContext] = useWorkspaceState(store, 'lab.offerContext', null);
  const [offerConfirmed, setOfferConfirmed] = useWorkspaceState(store, 'lab.offerConfirmed', false);
  const [gaps, setGaps] = useWorkspaceState(store, 'lab.gaps', '');
  const [feedback, setFeedback] = useWorkspaceState(store, 'lab.feedback', '');
  const [weeks, setWeeks] = useWorkspaceState(store, 'lab.weeks', 4);
  const [hours, setHours] = useWorkspaceState(store, 'lab.hours', 5);
  const [results, setResults] = useWorkspaceState(store, 'lab.results', {});
  const [checkedByPlan, setCheckedByPlan] = useWorkspaceState(store, 'lab.checkedByPlan', {});
  const planKey = results.roadmap?.id || 'legacy';
  const checked = checkedByPlan[planKey] || {};
  const setChecked = update => setCheckedByPlan(previous => ({ ...previous, [planKey]: typeof update === 'function' ? update(previous[planKey] || {}) : update }));
  const [filename, setFilename] = useWorkspaceState(store, 'lab.filename', '');
  const [history, setHistory] = useWorkspaceState(store, 'lab.history', []);
  const current = tools[tab];
  const result = results[tab];
  const fitStale = tab === 'fit' && result && (!result.input_snapshot || result.input_snapshot.role !== role.trim() || result.input_snapshot.cv !== cv.trim() || result.input_snapshot.description !== description.trim() || result.input_snapshot.demo !== demo);
  const latestReview = completed.find(record => record.type === 'CV review' && record.context?.cv);
  const latestInterview = completed.find(record => record.type === 'Mock interview');

  function tabKey(event, key) {
    if (busy || !['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const keys = Object.keys(tools), index = keys.indexOf(key);
    const next = event.key === 'Home' ? keys[0] : event.key === 'End' ? keys.at(-1) : keys[(index + (event.key === 'ArrowRight' ? 1 : -1) + keys.length) % keys.length];
    setTab(next); document.getElementById(`tab-${next}`)?.focus();
  }

  function loadReview() {
    if (!latestReview) return notify('Complete a CV review first, or paste your CV and review here.');
    setCV(latestReview.context.cv); setOfferConfirmed(false);
    if (!offerContext || tab !== 'fit') { setRole(latestReview.role); setDescription(latestReview.context.description || ''); setOfferContext(null); }
  }
  function loadFeedback() {
    if (!latestInterview) return notify('Complete a practice interview first, or paste feedback below.');
    setRole(latestInterview.role); setFeedback(JSON.stringify(latestInterview.report, null, 2));
  }
  // PSEUDOCODE: RUN A LAB TOOL
  // CAPTURE the selected tool and build its required payload.
  // CALL the matching backend route through the shared request handler.
  // SAVE the current result and prepend a dated history entry, keeping 50.
  // TRACK milestone checkboxes separately for each roadmap ID.
  function submit(event) {
    event.preventDefault();
    const target = tab;
    if (target === 'fit' && offerContext && !offerConfirmed) return notify('Check the original offer and confirm that the full requirements are included before analyzing.');
    run(async () => {
      const payload = { demo, role: role.trim() };
      if (target === 'jobs') Object.assign(payload, { location: location.trim() });
      if (target === 'fit') Object.assign(payload, { cv: cv.trim(), description: description.trim() });
      if (target === 'roadmap') Object.assign(payload, { cv: cv.trim(), gaps: gaps.trim(), feedback: feedback.trim(), weeks, hours });
      if (target === 'company') Object.assign(payload, { company: company.trim(), cv: cv.trim() });
      const response = await api(`/api/${tools[target].endpoint}`, payload);
      const saved = { id: crypto.randomUUID(), ...response, role: payload.role, company: payload.company, budget: hours, input_snapshot: { ...payload }, generated_at: new Date().toISOString() };
      const entry = { id: crypto.randomUUID(), tab: target, date: new Date().toISOString(), result: saved };
      await store.setMemory(previous => ({ ...previous, workspace: { ...previous.workspace,
        'lab.results': { ...previous.workspace?.['lab.results'], [target]: saved },
        'lab.history': [entry, ...(previous.workspace?.['lab.history'] || [])].slice(0, 50),
      } }));
    });
  }
  function upload(event) {
    const input = event.target, file = input.files[0];
    if (!file) return;
    if (file.size > 4 * 1024 * 1024) { input.value = ''; return notify('Choose a file of 4 MB or less.'); }
    run(async () => {
      try { const form = new FormData(); form.append('file', file); const data = await api('/api/extract', form); setCV(data.text); setFilename(file.name); }
      finally { input.value = ''; }
    });
  }
  // PSEUDOCODE: WORKFLOW HANDOFFS
  // COPY a selected listing into Job fit.
  // COPY fit gaps into Learning plan or company context into interview setup.
  // REUSE prior CV reviews and interview feedback instead of requiring re-entry.
  function chooseJob(job) {
    setRole(job.title); setDescription(job.offer_text || job.description);
    setOfferContext({ url: job.offer_source_url || job.url, status: job.offer_text_status || 'Summary only: paste the full offer requirements before analyzing.' }); setOfferConfirmed(false); setTab('fit');
    setResults(previous => ({ ...previous, fit: null }));
  }
  function makeRoadmap() {
    const match = results.fit;
    if (fitStale) return notify('Inputs changed. Rerun the fit analysis before creating a learning plan.');
    const gaps = roadmapGaps(match.analysis, match.input_snapshot?.cv || cv);
    if (match.input_snapshot) setCV(match.input_snapshot.cv);
    setGaps(gaps.map(item => `${item.skill}: ${item.reason}`).join('\n') || 'No missing requirements are established here. Use the CV evidence to plan an advanced practice task.');
    setRole(match.role); setTab('roadmap');
  }
  function practiceCompany() {
    const brief = results.company;
    const description = companyPracticeDescription(brief);
    if (!description) return notify('This saved company brief predates source-checked identity. Run company research again before starting an interview from it.');
    onPractice({ role: brief.role, description });
  }
  function download() {
    const link = document.createElement('a');
    const objectURL = URL.createObjectURL(new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' }));
    link.href = objectURL; link.download = `ai-career-coach-${tab}.json`; link.click();
    setTimeout(() => URL.revokeObjectURL(objectURL), 1000);
  }

  return <section className="page career-lab" id="career-lab">
    <CharacterGuide room="lab" /><div className="lab-welcome"><div className="lab-welcome-copy"><div className="eyebrow">WELCOME TO YOUR CAREER LAB</div><h1>A little curiosity.<br />A lot of possibility.</h1><p>Explore opportunities, experiment with your next move, and turn big ambitions into a plan.</p><span className="lab-welcome-sticker"><MemoryIcon name="flask" /> Train with a plan</span></div><LabArt /></div>
    <div className="panel"><p>{store.enabled ? "Results, drafts and milestone checkboxes are saved on this device." : "Saving is off. Enable it in My journey > Data settings to keep your work across visits."}</p><label htmlFor="lab-history">Previous Career Lab results</label><select id="lab-history" className="form-select" value="" disabled={busy} onChange={e => { const saved = history.find(item => item.id === e.target.value); if (saved && Object.hasOwn(tools, saved.tab)) { setTab(saved.tab); setResults(previous => ({ ...previous, [saved.tab]: saved.result })); } }}><option value="">Open a saved result...</option>{history.filter(item => Object.hasOwn(tools, item.tab)).map(item => <option key={item.id} value={item.id}>{tools[item.tab].label} - {item.result.role} - {new Date(item.date).toLocaleString()}</option>)}</select></div><div className="lab-discover"><span><MemoryIcon name="flask" /> FOUR TOOLS. YOUR NEXT BREAKTHROUGH.</span><p>Choose a training mission and plan your next move.</p></div>
    <div className="lab-tabs" role="tablist" aria-label="Career Lab tools">{Object.entries(tools).map(([key, tool]) => <button type="button" key={key} id={`tab-${key}`} role="tab" aria-selected={tab === key} aria-controls="lab-tool" tabIndex={tab === key ? 0 : -1} onKeyDown={event => tabKey(event, key)} className={`btn lab-tab ${tab === key ? 'selected' : ''}`} disabled={busy} onClick={() => setTab(key)}><span className={`lab-tab-icon tab-icon-${key}`}><MemoryIcon name={key === 'fit' ? 'target' : key} /></span>{tool.label}</button>)}</div>
    <div id="lab-tool" role="tabpanel" aria-labelledby={`tab-${tab}`}>
      <div className="lab-intro"><span className={`lab-active-icon tab-icon-${tab}`}><MemoryIcon name={tab === 'fit' ? 'target' : tab} /></span><div><h2>{current.heading}</h2><p>{current.intro}</p></div></div>
      <div className="lab-layout">
        <form id="lab-form" className="panel lab-form" onSubmit={submit} aria-busy={busy}>
          <label htmlFor="lab-role">Target role <span>*</span></label><input className="form-control" id="lab-role" value={role} onChange={e => setRole(e.target.value)} minLength={2} maxLength={160} placeholder="e.g. Frontend Developer" required />
          {tab === 'jobs' && <><label htmlFor="lab-location">Location <small>Optional</small></label><input className="form-control" id="lab-location" value={location} onChange={e => setLocation(e.target.value)} maxLength={160} placeholder="e.g. Berlin, Germany or remote" /><p className="privacy-copy">Live searches use your role and location only. Your CV is not included in the search.</p></>}
          {tab === 'company' && <><label htmlFor="lab-company">Company <span>*</span></label><input className="form-control" id="lab-company" value={company} onChange={e => setCompany(e.target.value)} minLength={2} maxLength={160} placeholder="Company name and country, if needed" required /><p className="privacy-copy">Live mode researches public company sources. CV context below personalizes rehearsal questions on the server and is not included in company web research.</p><button type="button" className="btn secondary" disabled={busy || !latestReview} onClick={loadReview}>Use latest CV review</button><label htmlFor="company-cv">CV context for rehearsal <small>Optional</small></label><textarea id="company-cv" className="form-control" rows={4} maxLength={30000} value={cv} onChange={e => setCV(e.target.value)} placeholder="Add your QA projects and responsibilities to personalize practice questions." /></>}
          {['fit', 'roadmap'].includes(tab) && <>
            <div className="lab-shortcuts"><button type="button" className="btn secondary" disabled={busy || !latestReview} onClick={loadReview}>Use latest CV review</button>{tab === 'roadmap' && <button type="button" className="btn secondary" disabled={busy || !latestInterview} onClick={loadFeedback}>Use interview feedback</button>}</div>
            <label htmlFor="lab-cv">Your CV <small>{tab === 'roadmap' ? 'Optional if you provide gaps or feedback' : 'Required'}</small></label><textarea className="form-control" id="lab-cv" rows={6} minLength={tab === 'roadmap' ? undefined : 80} maxLength={30000} required={tab !== 'roadmap'} value={cv} onChange={e => setCV(e.target.value)} placeholder="Paste your CV text or upload below…" />
            <label htmlFor="lab-file" className="form-label">Upload a CV <small>PDF, DOCX or TXT · up to 4 MB</small></label><input className="form-control" id="lab-file" type="file" accept=".pdf,.docx,.txt" disabled={busy} onChange={upload} />{filename && <small>{filename}</small>}
          </>}
          {tab === 'fit' && <>{offerContext && <aside className="alert alert-warning"><p>{offerContext.status}</p>{safeLink(offerContext.url) && <a href={offerContext.url} target="_blank" rel="noopener noreferrer">Check original offer</a>}<p>Include every requirement from the offer; a summary is insufficient for a comprehensive fit score.</p><label><input type="checkbox" checked={offerConfirmed} onChange={e => setOfferConfirmed(e.target.checked)} required /> I checked the source and included the full requirements.</label><button type="button" className="btn secondary" onClick={() => { setOfferContext(null); setOfferConfirmed(false); setDescription(''); }}>Enter a different offer</button></aside>}<label htmlFor="lab-description">Job description <small>{tab === 'fit' ? 'Required · paste the full offer for best results' : 'Optional'}</small></label><textarea className="form-control" id="lab-description" rows={6} value={description} onChange={e => { setDescription(e.target.value); setOfferConfirmed(false); }} required={tab === 'fit'} minLength={tab === 'fit' ? 20 : undefined} maxLength={12000} placeholder="Paste the specific job offer and its requirements…" /></>}
          {tab === 'roadmap' && <><label htmlFor="lab-gaps">Skills to work on <small>Optional</small></label><textarea className="form-control" id="lab-gaps" rows={3} value={gaps} onChange={e => setGaps(e.target.value)} maxLength={12000} placeholder="Use your job-fit result or add skills here…" /><label htmlFor="lab-feedback">Interview feedback <small>Optional</small></label><textarea className="form-control" id="lab-feedback" rows={3} value={feedback} onChange={e => setFeedback(e.target.value)} maxLength={18000} placeholder="What would you like to improve?" /><div className="row g-3"><div className="col-6"><label htmlFor="lab-weeks">Weeks</label><input className="form-control" id="lab-weeks" type="number" min={1} max={12} value={weeks} onChange={e => setWeeks(Number(e.target.value))} required /></div><div className="col-6"><label htmlFor="lab-hours">Hours per week</label><input className="form-control" id="lab-hours" type="number" min={1} max={20} value={hours} onChange={e => setHours(Number(e.target.value))} required /></div></div></>}
          {['fit', 'roadmap'].includes(tab) && <p className="privacy-copy">Live analysis sends this form’s text to OpenAI. Drafts and results are saved in this browser when device saving is enabled.</p>}
          <button type="submit" className="btn primary" disabled={busy}>{busy ? <><span className="spinner-border spinner-border-sm" aria-hidden="true" />Working on it…</> : current.action}</button>
        </form>
        <div className="lab-output" id="lab-output" aria-live="polite">
          {!result ? <aside className="tip-panel lab-empty"><div className="lab-empty-picture"><LabArt compact /><span className={`lab-empty-tool tab-icon-${tab}`}><MemoryIcon name={tab === 'fit' ? 'target' : tab} /></span></div><h3>A little curiosity.<br />A bigger possibility.</h3><p>Fill in your details to explore {current.label.toLowerCase()}.</p><small>{demo ? 'Demo mode shows illustrative results. Live job and company research requires an API key with web search access.' : 'Live research can take a little longer. Your inputs stay here if a request fails.'}</small></aside> : <>
            <div className={`alert ${result.demo ? 'demo-badge' : 'lab-live'}`}>{result.demo ? 'DEMO · Illustrative results, not live research or a performed AI assessment.' : 'LIVE AI · Generated guidance; verify details before acting.'}</div>
            <div className="lab-result-heading"><h2>{result.role}</h2><button className="btn secondary" type="button" onClick={download}>Download ↓</button></div>
            {tab === 'jobs' && <>{result.search_diagnostics && <details className="lab-sources"><summary>How many listings were found and filtered?</summary><p>Research returned {result.search_diagnostics.researched}; source links accepted: {result.search_diagnostics.source_accepted}; shown: {result.search_diagnostics.shown}.</p><p>Duplicate application targets removed: {result.search_diagnostics.duplicates_removed || 0}. Discarded source links: {result.search_diagnostics.source_rejected}. Location not supported: {result.search_diagnostics.checks?.location_not_supported || 0}. Pages unavailable or timed out: {result.search_diagnostics.checks?.page_unavailable || 0}. Closed or missing: {result.search_diagnostics.checks?.closed_or_missing || 0}.</p></details>}{result.location_policy && <p className="lab-muted">{result.location_policy}</p>}<p className="lab-result-summary">{result.demo ? result.summary : result.jobs.length ? `${result.jobs.length} source-backed job listing${result.jobs.length === 1 ? "" : "s"} returned. Check each source for current availability and location eligibility.` : "No source-backed job listings could be confirmed for this search. Try a more specific role, one location, or remote eligibility terms."}</p>{result.searched_at && <small className="lab-muted">Searched {new Date(result.searched_at).toLocaleString()} · Openings may have closed.</small>}{!result.jobs.length && <div className="panel"><h3>No matching job cards to display.</h3><p>Try a broader role or location. No invented listings were substituted.</p></div>}{result.jobs.map((job, i) => <article className="panel lab-job" key={i}><span className="lab-kicker">{result.demo ? 'FICTIONAL SAMPLE' : job.company}</span><h3>{job.title}</h3><p className="lab-muted">{job.company} · {job.location}{job.posted_at ? ` · Posted ${job.posted_at}` : ''}</p><p>{job.description}</p>{job.location_verified && job.location_evidence && <blockquote><strong>Workplace eligibility from source:</strong> {job.location_evidence.quote}<small className="d-block">{job.location_evidence.status}</small></blockquote>}{!result.demo && <p className="lab-muted">{job.link_status === 'application_found' ? 'Matching job page with an application option found when checked. Confirm availability with the employer.' : job.link_status === 'posting_found' ? 'Matching posting found when checked. Confirm availability with the employer.' : 'Availability unconfirmed: this page could not establish a matching current vacancy.'}</p>}<div className="lab-job-actions">{safeLink(job.url) && <a className="btn secondary" href={job.url} target="_blank" rel="noopener noreferrer">View source & offer ↗</a>}<button className="btn primary" type="button" onClick={() => chooseJob(job)}>Check my fit ↗</button></div></article>)}<Sources sources={result.sources?.filter(source => result.jobs.some(job => job.url === source.url))} title="Sources for displayed job listings" /></>}
            {fitStale && <div role="status" className="alert alert-warning"><strong>Inputs changed - rerun analysis.</strong><p>The previous score is hidden because it belongs to earlier or unrecorded inputs. Downloads retain the original analyzed snapshot when available.</p></div>}{tab === 'fit' && !fitStale && <><p className="lab-muted">Analyzed {result.generated_at ? new Date(result.generated_at).toLocaleString() : 'earlier inputs'}. Downloads and learning gaps use this analyzed input snapshot.</p><Score value={result.analysis.score} label="CV evidence match · not a hiring probability" /><p className="lab-result-summary">{plainProse(result.analysis.summary)}</p><article className="panel"><h3>What your CV already shows</h3>{result.analysis.matched_skills.length ? result.analysis.matched_skills.map((item, i) => <div className="lab-skill" key={i}><strong>{item.skill}</strong><blockquote>{item.evidence}</blockquote></div>) : <p>No matched skills identified from the supplied evidence.</p>}</article><article className="panel"><h3>Requirements not yet evidenced</h3>{result.analysis.missing_skills.length ? result.analysis.missing_skills.map((item, i) => <div className="lab-skill" key={i}><strong>{item.skill}</strong> <span className="badge lab-priority">{item.priority} priority</span><p>{item.reason}</p></div>) : <p>No additional gaps identified. That does not guarantee a match.</p>}</article><article className="panel"><h3>Make your next move</h3><Bullets items={result.analysis.improvements} /><button className="btn primary" type="button" onClick={makeRoadmap}>Turn this into a learning plan ↗</button></article></>}
            {tab === 'roadmap' && <><p className="lab-result-summary">{plainProse(result.plan.summary)}</p><p className="lab-muted">{result.plan.weeks.length} weeks · up to {result.budget} hours per week · {Object.values(checked).filter(Boolean).length} milestones checked off</p>{result.plan.weeks.map(week => <article className={`panel lab-week ${checked[week.week] ? 'milestone-done' : ''}`} key={week.week}><span className="lab-kicker">WEEK {week.week} · {week.activities.reduce((sum, item) => sum + item.hours, 0)} HOURS</span><h3>{week.focus}</h3>{week.scope_note && <p className="lab-muted">{week.scope_note}</p>}<ul className="lab-list">{week.activities.map((activity, i) => <li key={i}>{activity.task} <strong>({activity.hours}h)</strong></li>)}</ul><p><strong>Make:</strong> {week.deliverable}</p><p><strong>Check:</strong> {week.success_check}</p><p className="lab-muted"><strong>Look for:</strong> {week.resource_hint}</p>{week.resource_links?.length > 0 && <Sources sources={week.resource_links} title="Official documentation" />}{week.resource_status && week.resource_status !== 'matched' && <small className="lab-muted">{week.resource_status}</small>}<label className="lab-check"><input className="form-check-input" type="checkbox" checked={!!checked[week.week]} onChange={e => { const checked = e.target.checked; setChecked(previous => ({ ...previous, [week.week]: checked })); }} /> I completed this milestone</label></article>)}</>}
            {tab === 'company' && <><p className="lab-result-summary">{plainProse(result.brief.overview)}</p>{result.researched_at && <small className="lab-muted">Researched {new Date(result.researched_at).toLocaleString()}</small>}<Sources sources={result.sources} title="Sources supporting displayed claims" />{result.brief.culture_checks?.length > 0 && <aside className="lab-sources"><strong>Official culture-page checks</strong>{result.brief.culture_checks.map(check => <p key={check.url}><a href={safeLink(check.url)} target="_blank" rel="noopener noreferrer">{check.url}</a>: {check.status}</p>)}</aside>}{result.background_sources?.length > 0 && <details><summary>Discovery/background sources (not evidence for displayed claims)</summary><Sources sources={result.background_sources} /></details>}{result.brief.identity_facts?.length > 0 && <article className="panel"><h3>Source-checked company identity</h3>{result.brief.identity_facts.map((fact, i) => <p key={i}><strong>{fact.kind === 'parent' ? 'Parent organization' : 'Company name'}:</strong> {fact.value} <a href={safeLink(fact.source_url)} target="_blank" rel="noopener noreferrer">Official source ?</a></p>)}</article>}<article className="panel"><h3>Company values & signals</h3>{result.brief.research_coverage && <p className="lab-muted">{result.brief.research_coverage}</p>}{result.brief.values.length ? result.brief.values.map((item, i) => <div className="lab-skill" key={i}><strong>{item.value}</strong><p>{item.evidence}</p>{item.basis && <small>{item.basis}</small>}{!result.demo && <p className="lab-muted">{item.applicability || 'Saved source context: applicability to this specific employer, country and contract was not established. Confirm benefits with the recruiter.'}</p>}<a href={safeLink(item.source_url)} target="_blank" rel="noopener noreferrer">Supporting source ↗</a></div>) : <p>{result.demo ? 'No company values researched in demo mode.' : 'No values could be linked to a retrieved source.'}</p>}</article><article className="panel"><h3>Suggested practice topics</h3>{result.brief.topics.map((item, i) => <div className="lab-skill" key={i}><strong>{item.topic}</strong>{item.basis && <small className="lab-muted">{item.basis}</small>}<p>{item.reason}</p>{item.applicability && <p className="lab-muted">{item.applicability}</p>}{safeLink(item.source_url) && <a href={item.source_url} target="_blank" rel="noopener noreferrer">Source context ↗</a>}</div>)}</article><article className="panel"><h3>Questions to rehearse</h3><p className="lab-muted">Suggestions for practice, not confirmed company interview questions.</p>{result.brief.question_basis && <p className="lab-muted">{result.brief.question_basis}</p>}<Bullets items={result.brief.questions} /><button className="btn primary" type="button" onClick={practiceCompany}>Practice this interview ↗</button></article></>}
          </>}
        </div>
      </div>
    </div>
  </section>;
}
