import DojoMentor, { TurtlePortrait } from './DojoArt.jsx';

export default function LabArt({ compact = false }) {
  return <div className={`lab-art dojo-lab-scene ${compact ? 'lab-art-compact' : ''}`} aria-hidden="true">
    <svg className="dojo-lab-board" viewBox="0 0 340 250" fill="none">
      <ellipse cx="170" cy="229" rx="130" ry="12" fill="#345d47" opacity=".1" />
      <circle cx="170" cy="125" r="103" fill="#e1eddd" />
      <g stroke="#345d47" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
        <path d="M65 42H274V169H65Z" fill="#fff8e5" />
        <path d="M57 39H282M57 172H282M90 174L80 219M249 174L259 219" stroke="#997451" strokeWidth="7" />
        <path d="M91 72H155M91 85H137M91 118L109 102L127 114L151 94" />
        <path d="M207 64L236 81V113L207 130L178 113V81ZM207 64V96M178 81L207 96L236 81M207 96V130" fill="#bed29c" />
        <path d="M100 149L110 156L128 139M143 149H191" />
      </g>
    </svg>
    <div className="dojo-lab-turtle"><TurtlePortrait name="Donatello" /></div>
    <div className="dojo-lab-sensei"><DojoMentor compact /></div>
  </div>;
}
