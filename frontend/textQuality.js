export function plainProse(value = '') {
  return String(value).replace(/!?\[([^\]\n]+)\]\(\s*https?:\/\/[^\s)]+\s*\)/g, '$1')
    .replace(/\uE200[^\uE201]*\uE201|\uE202[^\uE201]*\uE201|\[\d+\]|\[citation[^\]]*\]/gi, '').replace(/[ \t]{2,}/g, ' ').trim();
}

export function roadmapGaps(analysis, cv = '') {
  const supportedEnglish = value => String(value).split('\n').some(line => {
    if (/\b(?:not|learning|studying|target|aiming|pursuing)\b|in progress/i.test(line)) return false;
    const match = line.match(/\benglish\b([^,;|\n]{0,60})/i);
    const following = match ? match[1].split(/\b(?:german|french|spanish|arabic|italian|portuguese)\b/i)[0] : '';
    return /\b(?:C1|C2|fluent|native|bilingual)\b/i.test(following) || /\b(?:C1|C2|fluent|native|bilingual)\b\s+english\b/i.test(line);
  });
  const english = supportedEnglish(cv) || (analysis.matched_skills || []).some(item => /\benglish\b/i.test(item.skill) && supportedEnglish(item.evidence));
  const matched = new Set((analysis.matched_skills || []).map(item => item.skill.toLowerCase().trim()));
  return (analysis.validated_gaps || analysis.missing_skills || []).filter(item => !matched.has(item.skill.toLowerCase().trim()) && !(english && /\benglish\b/i.test(item.skill)));
}

export function companyPracticeDescription(result) {
  if (result.demo) return `Company: ${result.company}\nDEMO: no company facts were researched.\n${plainProse(result.brief.overview)}`;
  if (!result.brief.practice_context) return null;
  return `Company: ${result.company}\n${plainProse(result.brief.practice_context)}`.slice(0, 12000);
}
