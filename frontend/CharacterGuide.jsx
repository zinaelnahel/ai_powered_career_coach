import { TurtlePortrait } from './DojoArt.jsx';

const guides = {
  interview: { name: 'Leonardo', color: '#5e9dbd', label: 'YOUR INTERVIEW TRAINING PARTNER', advice: 'Take a breath. One clear example at a time.' },
  cv: { name: 'Raphael', color: '#bf665f', label: 'YOUR CV TRAINING PARTNER', advice: 'Make every word count. Let your real experience do the talking.' },
  lab: { name: 'Donatello', color: '#9482b4', label: 'YOUR CAREER LAB PARTNER', advice: 'Get curious. Find the evidence, test your options, build a plan.' },
  stories: { name: 'Michelangelo', color: '#dc9b56', label: 'YOUR STORY COLLECTING PARTNER', advice: 'Small wins make great stories. Save yours for the next big moment.' },
};

export default function CharacterGuide({ room }) {
  const guide = guides[room];
  if (!guide) return null;
  return <aside className="character-guide" style={{ '--guide-color': guide.color }} aria-label={`${guide.name}, your training partner`}><TurtlePortrait name={guide.name} /><div><span>{guide.label}</span><h2>Train with {guide.name}.</h2><p>{guide.advice}</p></div></aside>;
}
