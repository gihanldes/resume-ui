/** Types mirroring the FastAPI response models. */

export type Severity = 'critical' | 'warning' | 'suggestion' | 'positive'

export type CategoryKey =
  | 'contact'
  | 'structure'
  | 'impact'
  | 'ats'
  | 'formatting'
  | 'keywords'

export interface Finding {
  id: string
  category: CategoryKey
  category_label: string
  severity: Severity
  title: string
  detail: string
  fix: string
  evidence: string[]
  penalty: number
  /** Present on priority entries from engine v1.1+: gain on the overall scale. */
  overall_gain?: number
  /** Engine v1.2+: the resume section this concerns; null = whole document. */
  section?: string | null
}

export interface CategoryScore {
  category: CategoryKey
  label: string
  description: string
  score: number
  weight: number
  finding_count: number
  critical_count: number
  applicable: boolean
}

export interface KeywordTerm {
  term: string
  weight: number
  in_resume: boolean
  variants: string[]
}

export interface KeywordReport {
  coverage: number
  matched_count: number
  total_count: number
  matched: KeywordTerm[]
  missing: KeywordTerm[]
}

export interface ContactSnapshot {
  name: string | null
  emails: string[]
  phones: string[]
  linkedin: string | null
  github: string | null
  websites: string[]
  location: string | null
  sensitive_fields: string[]
}

export interface ParsedSnapshot {
  contact: ContactSnapshot
  sections: { name: string; heading: string; word_count: number }[]
  detected_sections: string[]
  bullet_count: number
  date_ranges: {
    raw: string
    start_year: number
    end_year: number | null
    is_current: boolean
    section: string
  }[]
  gaps: { from: string; to: string; months: number }[]
  experience_months: number
  experience_years: number
  word_count: number
  page_count: number
  extraction: Record<string, unknown>
  band?: string
  verdict?: string
  priorities?: Finding[]
  /** Engine v1.1+: score if the listed priorities were fixed. */
  projected_score?: number
}

export interface AIPriorityAction {
  title: string
  why: string
  how: string
}

export interface AIBulletRewrite {
  original: string
  improved: string
  rationale: string
}

export interface AIReview {
  overall_impression: string
  estimated_level: string
  strengths: string[]
  weaknesses: string[]
  priority_actions: AIPriorityAction[]
  bullet_rewrites: AIBulletRewrite[]
  tailoring_notes: string[]
  red_flags: string[]
}

export interface Analysis {
  id: string
  resume_id: string
  status: 'pending' | 'complete' | 'failed'
  error: string | null
  target_role: string | null
  job_description: string | null
  overall_score: number
  category_scores: CategoryScore[]
  findings: Finding[]
  keyword_report: KeywordReport | null
  parsed_snapshot: ParsedSnapshot
  ai_review: AIReview | null
  ai_model: string | null
  ai_error: string | null
  engine_version: string
  duration_ms: number
  created_at: string
  resume_filename: string | null
  band: string | null
  verdict: string | null
  priorities: Finding[]
}

export interface AnalysisSummary {
  id: string
  resume_id: string
  status: string
  overall_score: number
  target_role: string | null
  created_at: string
  has_ai_review: boolean
  resume_filename: string | null
}

export interface Resume {
  id: string
  filename: string
  content_type: string
  file_size: number
  page_count: number
  word_count: number
  created_at: string
  analysis_count: number
  latest_score: number | null
}

export interface ResumeDetail extends Resume {
  raw_text: string
  extraction_meta: Record<string, unknown>
}

export interface User {
  id: string
  email: string
  full_name: string | null
  target_role: string | null
  created_at: string
}

export interface TokenPair {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface Health {
  status: string
  environment: string
  ai_available: boolean
  ai_model: string | null
  engine_version: string
}

export interface Stats {
  resume_count: number
  analysis_count: number
  best_score: number | null
  latest_score: number | null
  delta: number | null
}

export interface CompareSummary {
  id: string
  resume_id: string
  resume_filename: string | null
  overall_score: number
  band: string | null
  created_at: string
  target_role: string | null
}

export interface CompareCategoryDelta {
  category: CategoryKey
  label: string
  current: number
  baseline: number
  delta: number
}

export interface CompareFindingRef {
  id: string
  title: string
  severity: Severity
}

export interface CompareResult {
  current: CompareSummary
  baseline: CompareSummary
  delta: {
    overall: number
    categories: CompareCategoryDelta[]
    resolved: CompareFindingRef[]
    introduced: CompareFindingRef[]
    still_open: number
  }
}
