import { useEffect, useRef, useState } from 'react';

export const MEMORY_KEY = 'career-coach-memory-v1';
export const emptyMemory = () => ({ profile: { role: '', goal: '' }, stories: [], sessions: [], workspace: {} });
const TAB_KEY = MEMORY_KEY + '-tab-workspace';
const sharedWorkspaceKeys = new Set(['lab.history', 'lab.checkedByPlan']);
const privateWorkspace = workspace => Object.fromEntries(Object.entries(workspace || {}).filter(([key]) => !sharedWorkspaceKeys.has(key)));
function withTabWorkspace(shared, own) {
  return { ...shared, workspace: { ...Object.fromEntries(Object.entries(shared.workspace || {}).filter(([key]) => sharedWorkspaceKeys.has(key))), ...privateWorkspace(own.workspace) } };
}
function loadTabMemory() {
  const saved = loadMemory();
  try {
    if (!saved.enabled) { sessionStorage.removeItem(TAB_KEY); return saved; }
    const tab = JSON.parse(sessionStorage.getItem(TAB_KEY) || 'null');
    if (tab?.reset === (localStorage.getItem(MEMORY_KEY + '-reset') || '') && tab.workspace && typeof tab.workspace === 'object' && !Array.isArray(tab.workspace)) {
      saved.memory = withTabWorkspace(saved.memory, tab);
    } else sessionStorage.removeItem(TAB_KEY);
  } catch { /* Keep the validated shared snapshot if this tab has no usable draft. */ }
  return saved;
}
function saveTab(memory, saving) {
  if (saving) sessionStorage.setItem(TAB_KEY, JSON.stringify({ reset: localStorage.getItem(MEMORY_KEY + '-reset') || '', workspace: privateWorkspace(memory.workspace) }));
  else sessionStorage.removeItem(TAB_KEY);
}

// PSEUDOCODE: RESTORE DEVICE MEMORY
// READ the versioned localStorage record and validate saved data.
// RESTORE report dates and enforce report/story limits.
// IF missing, start empty and respect the remembered saving preference.
// IF unreadable, return empty memory with an error.
export function loadMemory() {
  try {
    if (localStorage.getItem(MEMORY_KEY + '-disabled') === 'true') return { enabled: false, memory: emptyMemory(), error: '' };
    const raw = localStorage.getItem(MEMORY_KEY);
    if (!raw) return { enabled: localStorage.getItem(MEMORY_KEY + '-disabled') !== 'true', memory: emptyMemory(), error: '' };
    const saved = JSON.parse(raw);
    if (saved.version !== 1 || !saved.memory || !Array.isArray(saved.memory.sessions) || !Array.isArray(saved.memory.stories) || typeof saved.memory.profile?.role !== 'string' || typeof saved.memory.profile?.goal !== 'string') throw new Error();
    const memory = saved.memory;
    memory.workspace = memory.workspace && typeof memory.workspace === 'object' && !Array.isArray(memory.workspace) ? memory.workspace : {};
    memory.sessions = memory.sessions.filter(r => ['CV review', 'Mock interview'].includes(r.type) && typeof r.role === 'string' && typeof r.demo === 'boolean' && Number.isFinite(new Date(r.date).getTime()) && Number.isFinite(r.report?.score) && typeof r.report.summary === 'string' && ['strengths', 'improvements', 'next_steps'].every(k => Array.isArray(r.report[k]) && r.report[k].every(v => typeof v === 'string'))).slice(0, 50).map(r => ({ ...r, date: new Date(r.date) }));
    memory.stories = memory.stories.filter(s => typeof s.id === 'string' && ['title', 'skill', 'source', 'situation', 'task', 'action', 'result'].every(k => typeof s[k] === 'string')).slice(0, 100);
    return { enabled: true, memory, error: '' };
  } catch { return { enabled: false, memory: emptyMemory(), error: 'Saved career memory could not be loaded. Device storage may be unavailable or damaged.' }; }
}

// PSEUDOCODE: CROSS-TAB PERSISTENCE
// SERIALIZE read/change/write transactions with a same-origin Web Lock.
// APPLY functional edits to the latest saved data, never a stale tab snapshot.
// LISTEN for other tabs without writing their snapshots back.
// PROPAGATE saving preferences and full deletion; suppress pre-deletion queued edits.
export function useCareerMemory() {
  const [initial] = useState(loadTabMemory);
  const [memory, renderMemory] = useState(initial.memory);
  const [enabled, renderEnabled] = useState(initial.enabled);
  const [error, setError] = useState(initial.error);
  const [resetToken, setResetToken] = useState(() => {
    try { return localStorage.getItem(MEMORY_KEY + '-reset') || ''; } catch { return ''; }
  });
  const current = useRef(initial.memory);
  const seenReset = useRef(resetToken);
  const committed = useRef(initial.memory);
  const pending = useRef(0);
  function show(next, saving) {
    current.current = next; renderMemory(next); renderEnabled(saving);
  }
  function transaction(edit, { preference, erase = false, isEdit = false } = {}) {
    if (isEdit) pending.current += 1;
    let reset;
    try { reset = localStorage.getItem(MEMORY_KEY + '-reset'); }
    catch { reset = null; }
    const commit = () => {
      try {
        if (!erase && localStorage.getItem(MEMORY_KEY + '-reset') !== reset) return false;
        const saved = loadMemory();
        if (saved.error) throw new Error(saved.error);
        const saving = preference ?? saved.enabled;
        const base = saved.enabled && localStorage.getItem(MEMORY_KEY) ? withTabWorkspace(saved.memory, committed.current) : committed.current;
        const next = erase ? emptyMemory() : edit(base);
        if (erase) {
          const token = crypto.randomUUID();
          localStorage.setItem(MEMORY_KEY + '-reset', token); seenReset.current = token; setResetToken(token);
        }
        localStorage.setItem(MEMORY_KEY + '-disabled', String(!saving));
        if (saving) localStorage.setItem(MEMORY_KEY, JSON.stringify({ version: 1, memory: next }));
        else localStorage.removeItem(MEMORY_KEY);
        saveTab(next, saving);
        committed.current = next;
        // A completed save must not roll back newer keystrokes still queued.
        if (erase || pending.current <= (isEdit ? 1 : 0)) show(next, saving);
        else renderEnabled(saving);
        setError(navigator.locks ? '' : 'This browser cannot lock saves across tabs. Use one tab when editing saved data.');
        return true;
      } catch {
        show(erase ? emptyMemory() : edit(current.current), preference ?? enabled);
        setError('Device storage is unavailable or full. Your latest changes are only available until you leave. Export a backup.');
      } finally { if (isEdit) pending.current -= 1; }
    };
    if (navigator.locks) return navigator.locks.request(MEMORY_KEY, commit).catch(() => setError('The save could not acquire a browser lock. Please retry.'));
    return commit();
  }
  function setMemory(update, { optimistic = false } = {}) {
    // An AI request started before full deletion must not restore its old result.
    try { if ((localStorage.getItem(MEMORY_KEY + '-reset') || '') !== resetToken) return false; } catch { /* storage error is reported by transaction */ }
    const edit = previous => typeof update === 'function' ? update(previous) : update;
    const visitBase = current.current;
    if (optimistic) show(edit(visitBase), enabled);
    return transaction(edit, { isEdit: true });
  }
  function setEnabled(value) { renderEnabled(value); return transaction(previous => previous, { preference: value }); }
  function clear() { return transaction(() => emptyMemory(), { preference: false, erase: true }); }
  useEffect(() => {
    function sync(event) {
      // Handle only this app's shared keys.
      if (event.key !== null && ![MEMORY_KEY, MEMORY_KEY + '-disabled', MEMORY_KEY + '-reset'].includes(event.key)) return;
      const refresh = () => {
        // Read under the same lock as writers: reset, preference and content
        // are separate storage keys and must be observed as one transaction.
        const saved = loadMemory();
        if (saved.error) { setError(saved.error); return; }
        const token = localStorage.getItem(MEMORY_KEY + '-reset') || '';
        if (token !== seenReset.current || event.key === null) {
          seenReset.current = token; setResetToken(token);
          committed.current = saved.enabled ? saved.memory : emptyMemory();
          show(committed.current, saved.enabled);
          sessionStorage.removeItem(TAB_KEY);
        }
        else if (saved.enabled && !pending.current) { committed.current = withTabWorkspace(saved.memory, committed.current); show(committed.current, true); }
        else { renderEnabled(saved.enabled); if (!saved.enabled) sessionStorage.removeItem(TAB_KEY); }
      };
      if (navigator.locks) navigator.locks.request(MEMORY_KEY, refresh).catch(() => setError('Could not synchronize this tab. Refresh before editing saved data.'));
      else refresh();
    }
    window.addEventListener('storage', sync);
    return () => window.removeEventListener('storage', sync);
  }, []);
  return { memory, setMemory, enabled, setEnabled, error, clear, resetToken };
}

// Keep tool drafts and results in the same exportable, erasable device store.
// PSEUDOCODE: PERSISTENT FIELD HOOK
// READ a named workspace value or its default.
// UPDATE that field using the latest shared memory snapshot.
// LET the parent persistence hook save the changed workspace.
export function useWorkspaceState(store, key, fallback) {
  const value = store.memory.workspace?.[key] ?? fallback;
  function update(next) {
    return store.setMemory(previous => {
      const current = previous.workspace?.[key] ?? fallback;
      return { ...previous, workspace: { ...previous.workspace, [key]: typeof next === 'function' ? next(current) : next } };
    }, { optimistic: ['string', 'number', 'boolean'].includes(typeof next) });
  }
  return [value, update];
}
