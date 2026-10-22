export function DojoIcon({ name = 'spark', className = '' }) {
  const aliases = { journey: 'progress', brain: 'memory', flask: 'lab', practice: 'interview', bank: 'memory', story: 'cv', star: 'spark' };
  const paths = {
    about: <><path d="M5 8C0 7 2 2 5 4L7 6M17 6L19 4C23 2 24 7 19 8M5 8Q12 2 19 8V14L16 18L12 22L8 18L5 14Z" /><path d="M8 10H10M14 10H16M10 14L12 16L14 14M2 13L7 14M17 14L22 13" /></>,
    overview: <><path d="M3 5Q12 8 21 5M4 10H20M7 8V21M17 8V21M4 21H20" /><circle cx="12" cy="3" r=".6" /></>,
    interview: <><path d="M3 10Q3 3 11 3Q19 3 19 10V15Q17 20 11 20Q5 20 3 15ZM3 8Q11 11 19 8V13Q11 11 3 13ZM19 10L23 7L22 12L19 13M19 13L23 16L20 18M7 10H8M14 10H15M8 16Q11 18 14 16" /></>,
    cv: <><path d="M6 3H19Q22 3 22 6H9Q9 3 6 3Q3 3 3 6V8H6V18Q6 21 9 21H19Q16 21 16 18H6M19 6V18H16" /><path d="M10 10H15M10 13H15" /></>,
    lab: <><path d="M4 6Q12 2 20 6V11Q12 15 4 11ZM4 8L1 5V11L4 10M20 8L23 5V11L20 10M7 8H9M15 8H17M6 16L9 21L12 18L15 21L18 16M9 17H15" /></>,
    progress: <><path d="M3 9L10 8M14 8L21 9V13L14 12M10 12L3 13Z" /><path d="M10 8L13 7L15 10L12 13L9 11ZM11 13L8 20L6 17L9 12M14 12L17 19L18 16L15 12" /></>,
    memory: <><path d="M5 4H19V20H5ZM3 3H21M3 21H21" /><path d="M12 7L17 10V15L12 18L7 15V10ZM12 7V12M7 10L12 12L17 10M12 12V18" /></>,
    microphone: <><rect x="9" y="2" width="6" height="13" rx="3" /><path d="M9 6H15M9 9H15M15 7L19 5L18 9M5 10V12A7 7 0 0 0 19 12V10M12 19V22M8 22H16" /></>,
    stop: <rect x="5" y="5" width="14" height="14" rx="3" />,
    upload: <><path d="M5 14V21H19V14M3 21H21M12 16V3M7 8L12 3L17 8M7 17H9M15 17H17" /></>,
    mentor: <><path d="M5 8C0 7 2 2 5 4L7 6M17 6L19 4C23 2 24 7 19 8M5 8Q12 2 19 8V14L16 18L12 22L8 18L5 14Z" /><path d="M8 10H10M14 10H16M10 14L12 16L14 14M2 13L7 14M17 14L22 13" /></>,
    trainee: <><path d="M12 3L19 7L21 14L17 21H7L3 14L5 7Z" /><path d="M12 8L17 11V16L12 19L7 16V11ZM12 3V8M19 7L17 11M21 14L17 14M17 21L12 19M7 21L9 18M3 14H7M5 7L7 11" /></>,
    jobs: <><path d="M3 4H21V16H3ZM6 7H12M6 10H10M6 13H14M7 16L4 21M17 16L20 21" /><path d="M16 7L19 8V11L16 13L13 11V8Z" /></>,
    roadmap: <><path d="M5 3H19V21H5M3 3H21M3 21H21M8 17L11 13L9 10L15 7M13 7H16V10" /></>,
    company: <><path d="M3 21H21M5 21V8H19V21M3 4Q12 7 21 4M4 8H20M9 21V16H15V21M8 11H10M14 11H16" /></>,
    target: <><circle cx="11" cy="13" r="8" /><circle cx="11" cy="13" r="4" /><path d="M11 13L21 3M17 3H21V7" /></>,
    shield: <><path d="M12 2L20 6L22 14L17 21H7L2 14L4 6ZM12 7L17 10V15L12 18L7 15V10ZM12 2V7M4 6L7 10M20 6L17 10M2 14H7M22 14H17M12 18V21" /></>,
    spark: <><path d="M4 3Q12 0 20 3L12 22ZM4 3Q12 7 20 3" /><circle cx="10" cy="10" r="1.5" /><circle cx="14" cy="7" r="1" /><path d="M12 15H13" /></>,
  };
  const key = aliases[name] || name;
  return <svg className={`dojo-icon ${className}`} data-dojo-icon={key} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.65" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">{paths[key] || paths.spark}</svg>;
}
