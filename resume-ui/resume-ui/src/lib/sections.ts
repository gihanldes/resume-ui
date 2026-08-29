/** Display names for the resume's canonical sections, plus the document group. */
export const SECTION_LABELS: Record<string, string> = {
  document: 'Whole document',
  header: 'Contact header',
  summary: 'Summary',
  experience: 'Experience',
  education: 'Education',
  skills: 'Skills',
  projects: 'Projects',
  certifications: 'Certifications',
  awards: 'Awards',
  publications: 'Publications',
  volunteer: 'Volunteering',
  languages: 'Languages',
  interests: 'Interests',
  references: 'References',
}

export function sectionLabel(key: string): string {
  return SECTION_LABELS[key] ?? key.charAt(0).toUpperCase() + key.slice(1)
}
