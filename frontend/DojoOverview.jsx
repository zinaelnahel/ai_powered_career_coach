import DojoMentor, { TrainingIcon, TurtlePortrait, PizzaProgress } from './DojoArt.jsx';

const belts = [
  { name: 'White', threshold: 0, color: '#F1EADD', title: 'The beginning is a skill, too.' },
  { name: 'Green', threshold: 100, color: '#9CB9A0', title: 'Consistency is taking root.' },
  { name: 'Blue', threshold: 250, color: '#90B8CF', title: 'Your experience is finding its voice.' },
  { name: 'Purple', threshold: 500, color: '#B3A0C8', title: 'Practice is becoming a habit.' },
  { name: 'Black', threshold: 1000, color: '#34473F', title: 'Keep the curiosity. Keep training.' },
];

// PSEUDOCODE: DOJO PROGRESS
// DERIVE practice points from saved completed activities, never AI assessment scores.
// RECOMPUTE after deletion; existing data counts and full memory deletion resets progress.
export function dojoProgress(memory) {
  const sessions = memory.sessions || [];
  const interviews = sessions.filter(item => item.type === 'Mock interview').length;
  const reviews = sessions.filter(item => item.type === 'CV review').length;
  const stories = memory.stories?.length || 0;
  const checked = memory.workspace?.['lab.checkedByPlan'] || {};
  const milestones = Object.values(checked).reduce((sum, plan) => sum + Object.values(plan || {}).filter(value => value === true).length, 0);
  const points = interviews * 75 + reviews * 50 + stories * 30 + milestones * 25;
  const beltIndex = belts.reduce((current, belt, index) => points >= belt.threshold ? index : current, 0);
  return { interviews, reviews, stories, milestones, points, belt: belts[beltIndex], next: belts[beltIndex + 1] };
}

const rooms = [
  { key: 'interview', guide: 'Leonardo', number: '01', label: 'THE SPEAKING ROOM', title: 'Find your interview voice.', description: 'One question at a time. Real examples. A little more confidence.', action: 'Mock interview', reward: '75 points / session', color: 'sage' },
  { key: 'cv', guide: 'Raphael', number: '02', label: 'THE STORY WORKSHOP', title: 'Give your experience an edge.', description: 'Turn your CV into a clear story of what you bring to the team.', action: 'CV reviewer', reward: '50 points / review', color: 'peach' },
  { key: 'lab', guide: 'Donatello', number: '03', label: 'THE EXPLORATION GARDEN', title: 'Prepare your next move.', description: 'Find jobs, check your fit, plan your learning, and research companies.', action: 'Career Lab', reward: '25 points / milestone', color: 'lilac' },
  { key: 'memory', guide: 'Michelangelo', number: '04', label: 'THE SCROLL LIBRARY', title: 'Collect your proof.', description: 'Save real achievements and shape them into interview-ready STAR stories.', action: 'Goals & stories', reward: '30 points / story', color: 'sand' },
];

export default function DojoOverview({ navigate, store }) {
  const progress = dojoProgress(store.memory);
  const { belt, next, points } = progress;
  const fill = next ? Math.min(100, Math.round((points - belt.threshold) / (next.threshold - belt.threshold) * 100)) : 100;
  const missions = [
    { title: 'Find your voice', detail: 'Complete one mock interview.', count: progress.interviews, total: 1, page: 'interview', icon: 'interview' },
    { title: 'Sharpen your story', detail: 'Complete one CV review.', count: progress.reviews, total: 1, page: 'cv', icon: 'cv' },
    { title: 'Build your story toolkit', detail: 'Save three reviewed STAR stories.', count: progress.stories, total: 3, page: 'memory', icon: 'memory' },
  ];
  const nextMission = missions.find(mission => mission.count < mission.total);
  const activities = progress.interviews + progress.reviews + progress.stories + progress.milestones;
  const slices = activities === 0 ? 0 : activities % 8 || 8;
  const pizzas = Math.floor(activities / 8);
  const badges = [
    { name: 'First words', earned: progress.interviews >= 1, icon: 'interview', hint: 'Complete an interview' },
    { name: 'Story sharpener', earned: progress.reviews >= 1, icon: 'cv', hint: 'Complete a CV review' },
    { name: 'Proof collector', earned: progress.stories >= 3, icon: 'memory', hint: 'Save three STAR stories' },
    { name: 'Steady steps', earned: progress.milestones >= 1, icon: 'progress', hint: 'Check off a learning milestone' },
  ];
  return <section id="overview" className="page dojo-overview">
    <div className="dojo-page-heading"><div><div className="dojo-kicker">YOUR NEXT CHAPTER STARTS WITH PRACTICE</div><h1>Welcome to your dojo<span>.</span></h1><p>A little practice. A stronger story. A career that feels like you.</p></div><span className="dojo-edition-label">TRAIN AT YOUR OWN PACE</span></div>
    <div className="dojo-top-grid">
      <article className="dojo-welcome">
        <div className="dojo-hero-copy"><div className="dojo-hero-label"><span /> MEET YOUR CAREER MENTOR</div><h2>Big ambitions.<br />Small, steady steps.</h2><p>I'm Master Splinter. Bring your real experience.<br />We'll turn it into your next opportunity.</p><button className="dojo-button gold" onClick={() => navigate(nextMission?.page || 'interview')}>{nextMission ? 'Start your next mission' : 'Keep practicing'} <span aria-hidden="true">&#8599;</span></button><span className="dojo-hero-footnote">No perfect answers required. Just a place to begin.</span></div>
        <div className="dojo-mentor-scene"><div className="dojo-sun" /><div className="dojo-window" /><div className="dojo-bamboo bamboo-one" /><div className="dojo-bamboo bamboo-two" /><DojoMentor /><span className="dojo-mentor-name">MASTER SPLINTER <span>YOUR CAREER SENSEI</span></span></div>
      </article>
      <article className="dojo-belt-card"><div className="dojo-card-label">YOUR TRAINING JOURNEY <TrainingIcon name="star" /></div><div className="dojo-belt" style={{ '--belt-color': belt.color }} aria-hidden="true"><i /><b /><i /></div><span className="dojo-belt-name">{belt.name} belt</span><h2>{belt.title}</h2><div className="dojo-point-count"><strong>{points}</strong><span>practice points</span></div><div className="dojo-meter" role="progressbar" aria-label={next ? `Progress to ${next.name.toLowerCase()} belt` : 'Highest belt reached'} aria-valuenow={fill} aria-valuemin={0} aria-valuemax={100}><span style={{ width: `${fill}%` }} /></div><p>{next ? `${next.threshold - points} points to your ${next.name.toLowerCase()} belt` : 'Every practice still counts.'}</p><button className="dojo-inline-link" onClick={() => navigate('progress')}>View practice history <span aria-hidden="true">&#8594;</span></button></article>
    </div>
    <div className="dojo-section-heading"><div><span className="dojo-kicker">FOUR ROOMS. YOUR OWN PACE.</span><h2>Choose your training ground.</h2></div><span className="dojo-heading-note">Every room is open to you.</span></div>
    <div className="dojo-rooms">{rooms.map(room => <article className={`dojo-room room-${room.color}`} key={room.key}><div className="dojo-room-top"><TurtlePortrait name={room.guide} /><span className="dojo-room-number">{room.number}</span></div><span className="dojo-room-guide">TRAIN WITH {room.guide.toUpperCase()}</span><span className="dojo-room-label">{room.label}</span><h3>{room.title}</h3><p>{room.description}</p><div className="dojo-room-footer"><small>{room.reward}</small><button onClick={() => navigate(room.key)} aria-label={`Open ${room.action}`}>{room.action} <span aria-hidden="true">&#8599;</span></button></div></article>)}</div>
    <article className="dojo-pizza-card"><PizzaProgress slices={slices} /><div className="dojo-pizza-copy"><span className="dojo-kicker">A LITTLE PRACTICE. A LITTLE PIZZA.</span><h2>{slices === 8 ? 'Pizza party unlocked!' : 'Every small win earns a slice.'}</h2><p>One saved activity, one slice. Interviews, CV reviews, stories and learning milestones all count.</p></div><div className="dojo-pizza-status"><strong>{slices}<span>/8 slices</span></strong><small>{pizzas > 0 ? `${pizzas} full ${pizzas === 1 ? 'pizza' : 'pizzas'} earned` : 'Your first pizza is in the making.'}</small><button className="dojo-inline-link" onClick={() => navigate(nextMission?.page || 'interview')}>Earn your next slice <span aria-hidden="true">&#8594;</span></button></div></article>
    <div className="dojo-bottom-grid">
      <article className="dojo-missions"><div className="dojo-section-heading"><div><span className="dojo-kicker">YOUR FIRST CHAPTER</span><h2>Three small missions.</h2></div><span className="dojo-count">{missions.filter(m => m.count >= m.total).length}/3 complete</span></div>{missions.map(mission => <div className={`dojo-mission ${mission.count >= mission.total ? 'done' : ''}`} key={mission.title}><span className="dojo-mission-check" aria-hidden="true">{mission.count >= mission.total ? '\u2713' : <TrainingIcon name={mission.icon} />}</span><div><h3>{mission.title}</h3><p>{mission.detail}</p></div><span className="dojo-mission-count">{Math.min(mission.count, mission.total)}/{mission.total}</span><button className="dojo-inline-link" onClick={() => navigate(mission.page)} aria-label={`${mission.count >= mission.total ? 'Revisit' : 'Start'} ${mission.title}`}>{mission.count >= mission.total ? 'Revisit' : 'Train'} <span aria-hidden="true">&#8594;</span></button></div>)}</article>
      <article className="dojo-badges"><span className="dojo-kicker">LITTLE WINS, COLLECTED</span><h2>Your practice badges.</h2><div className="dojo-badge-grid">{badges.map(badge => <div className={`dojo-badge ${badge.earned ? 'earned' : ''}`} key={badge.name} title={badge.hint}><span><TrainingIcon name={badge.icon} /></span><strong>{badge.name}</strong><small>{badge.earned ? 'Earned' : badge.hint}</small></div>)}</div></article>
    </div>
    <p className="dojo-progress-note">Points celebrate practice, never AI scores. Based on currently saved reports, stories and checked milestones; demo activities count too. {store.enabled ? 'Your progress stays in this browser.' : 'Device saving is off; progress lasts for this visit.'} <button onClick={() => navigate('settings')}>Manage saved data</button></p>
  </section>;
}
