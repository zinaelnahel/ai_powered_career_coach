import { DojoIcon } from './DojoIcons.jsx';
import { useEffect, useRef, useState } from 'react';

// PSEUDOCODE: BROWSER DICTATION
// DETECT supported speech recognition and maintain microphone UI state.
// KEEP current callbacks in a ref so speech events use fresh state.
// CANCEL on navigation, hidden tab or unmount; preserve the text fallback.
export default function Dictation({ active, disabled, append, onActive }) {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const instance = useRef(null);
  const callbacks = useRef({ append, onActive });
  callbacks.current = { append, onActive };
  const [listening, setListening] = useState(false);
  const [interim, setInterim] = useState('');
  const [message, setMessage] = useState('');
  const [language, setLanguage] = useState('en-US');
  // PSEUDOCODE: CANCEL LISTENING
  // DETACH the active recognizer before aborting it.
  // CLEAR temporary text and release the listening flag.
  // IGNORE any late events from the detached recognizer.
  function cancel() {
    const recognition = instance.current;
    instance.current = null;
    recognition?.abort();
    setListening(false); setInterim(''); callbacks.current.onActive(false);
  }
  useEffect(() => {
    if (!active || disabled) cancel();
  }, [active, disabled]);
  useEffect(() => {
    const hide = () => { if (document.hidden) cancel(); };
    document.addEventListener('visibilitychange', hide);
    return () => {
      document.removeEventListener('visibilitychange', hide);
      const recognition = instance.current;
      instance.current = null;
      recognition?.abort();
      callbacks.current.onActive(false);
    };
  }, []);
  // PSEUDOCODE: DICTATION EVENT FLOW
  // CREATE one recognizer with selected language and interim results.
  // ON results, append final text and display provisional text separately.
  // ON errors, show guidance and cancel; on end, release listening state.
  // START only after the user clicks the dictation button.
  function start() {
    if (instance.current || !Recognition || disabled || !active) return;
    const recognition = new Recognition();
    instance.current = recognition;
    recognition.lang = language;
    recognition.continuous = true;
    recognition.interimResults = true;
    setMessage(''); setListening(true); callbacks.current.onActive(true);
    recognition.onresult = event => {
      if (instance.current !== recognition) return;
      const final = [], pending = [];
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        (result.isFinal ? final : pending).push(result[0].transcript);
      }
      if (final.length) callbacks.current.append(final.join(' '));
      setInterim(pending.join(' '));
    };
    recognition.onerror = event => {
      if (instance.current !== recognition) return;
      const errors = {
        'not-allowed': 'Microphone access was denied. Allow it in your browser site settings, or type your answer.',
        'service-not-allowed': 'Your browser has disabled speech recognition. You can still type your answer.',
        'audio-capture': 'No microphone is available. Check your microphone connection.',
        'no-speech': 'No speech detected. Try dictating again.',
        network: 'Speech recognition could not connect. Check your connection and try again.',
        'language-not-supported': 'This dictation language is unavailable in your browser. Choose another language.'
      };
      setMessage(errors[event.error] || 'Dictation stopped. You can retry or type your answer.');
      cancel();
    };
    recognition.onend = () => {
      if (instance.current !== recognition) return;
      instance.current = null;
      setListening(false); setInterim(''); callbacks.current.onActive(false);
    };
    try { recognition.start(); }
    catch { cancel(); setMessage('Could not start dictation. Try again or type your answer.'); }
  }
  if (!Recognition) return <p className="privacy-copy">Voice dictation is unavailable in this browser. You can type your answer.</p>;
  return <div className="dictation-controls">
    <div className="d-flex flex-wrap align-items-center gap-2 my-2">
      <button type="button" className="btn secondary" disabled={disabled || !active} aria-pressed={listening} onClick={() => listening ? instance.current?.stop() : start()}><DojoIcon name={listening ? 'stop' : 'microphone'} />{listening ? 'Stop dictation' : 'Dictate answer'}</button>
      <label htmlFor="dictation-language">Dictation language</label>
      <select id="dictation-language" className="form-select w-auto" value={language} disabled={listening || disabled} onChange={e => setLanguage(e.target.value)}>
        <option value="en-US">English (US)</option><option value="en-GB">English (UK)</option><option value="de-DE">German</option><option value="fr-FR">French</option><option value="es-ES">Spanish</option>
      </select>
    </div>
    <p role="status">{message || (listening ? 'Listening... Stop dictation before editing or sending your answer.' : 'Dictate, then review and edit your answer before sending.')}{interim && <span className="d-block">{interim}</span>}</p>
    <p className="privacy-copy">Your browser may send audio to its speech service. This app saves only the text when device saving is enabled. No transcription API charges are added by this app.</p>
  </div>;
}
