import type { ReactNode } from 'react'
import type { AIReview, KeywordReport, ParsedSnapshot } from '../types'
import { Notice } from './ui'
import { CoverageRing } from './art'

/* ------------------------------------------------------------- job match */
export function KeywordPanel({ report }: { report: KeywordReport }) {
  const pct = Math.round(report.coverage * 100)
  return (
    <section className="mt-9 border-t border-ink-line pt-6" aria-label="Job description match">
      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
        <h2 className="section-title">Job match</h2>
        <span className="text-[13.5px] text-ink-muted">
          <CoverageRing coverage={report.coverage} />{' '}
          <span className="font-mono font-semibold text-ink-text">{pct}%</span> ·{' '}
          {report.matched_count} of {report.total_count} weighted terms covered
        </span>
      </div>

      {report.missing.length > 0 && (
        <div className="mt-4">
          <h3 className="text-[13.5px] font-semibold text-[color:var(--color-mark-critical)]">
            No evidence in resume
          </h3>
          <p className="mt-1.5 font-mono text-[13px] leading-relaxed text-[color:var(--color-mark-critical)]">
            {report.missing.map((term, index) => (
              <span key={term.term}>
                {index > 0 && <span className="text-ink-dim"> · </span>}
                {term.term}
              </span>
            ))}
          </p>
        </div>
      )}

      {report.matched.length > 0 && (
        <div className="mt-4">
          <h3 className="text-[13.5px] font-semibold text-ink-muted">Covered</h3>
          <p className="mt-1.5 font-mono text-[13px] leading-relaxed text-ink-muted">
            {report.matched.map((term, index) => (
              <span key={term.term}>
                {index > 0 && <span className="text-ink-dim"> · </span>}
                {term.term}
              </span>
            ))}
          </p>
        </div>
      )}

      <p className="mt-4 max-w-[640px] text-[13px] leading-relaxed text-ink-dim">
        Only add a term you could discuss in an interview. A keyword you can't back up fails at
        the next stage instead of this one.
      </p>
    </section>
  )
}

/* ------------------------------------------------------------ AI review */
export function AIPanel({
  review,
  error,
  model,
  action,
}: {
  review: AIReview | null
  error: string | null
  model: string | null
  action?: ReactNode
}) {
  if (!review) {
    return (
      <div aria-label="AI review">
        <h2 className="section-title">AI review</h2>
        <div className="mt-3 max-w-[640px]">
          <Notice tone="info">{error ?? 'No AI review was run for this analysis.'}</Notice>
        </div>
        {action && <div className="mt-4">{action}</div>}
      </div>
    )
  }

  return (
    <div aria-label="AI review">
      <div className="flex flex-wrap items-baseline gap-x-4">
        <h2 className="section-title">AI review</h2>
        {model && <span className="font-mono text-[12.5px] text-ink-dim">{model}</span>}
      </div>

      <p className="mt-3 max-w-[680px] text-[15px] leading-relaxed text-ink-text">
        {review.overall_impression}
      </p>

      <p className="mt-2 text-[13.5px] text-ink-muted">
        Reads as <span className="font-medium text-ink-text">{review.estimated_level}</span>
      </p>

      {review.red_flags.length > 0 && (
        <div className="mt-6">
          <h3 className="text-[13.5px] font-semibold text-[color:var(--color-mark-critical)]">
            Red flags
          </h3>
          <ul className="mt-2 max-w-[640px] space-y-1.5 text-sm leading-relaxed text-ink-muted">
            {review.red_flags.map((flag, i) => (
              <li key={i}>{flag}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-6 grid gap-x-10 gap-y-6 sm:grid-cols-2">
        <div>
          <h3 className="text-[13.5px] font-semibold text-brand">Working</h3>
          <ul className="mt-2 space-y-2 text-sm leading-relaxed text-ink-muted">
            {review.strengths.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </div>
        <div>
          <h3 className="text-[13.5px] font-semibold text-[color:var(--color-mark-warning)]">
            Holding you back
          </h3>
          <ul className="mt-2 space-y-2 text-sm leading-relaxed text-ink-muted">
            {review.weaknesses.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </div>
      </div>

      {review.priority_actions.length > 0 && (
        <div className="mt-7">
          <h3 className="text-[13.5px] font-semibold text-ink-text">Do these in order</h3>
          <ol className="mt-2">
            {review.priority_actions.map((item, i) => (
              <li
                key={i}
                className="flex gap-4 border-b border-ink-faint py-3.5 last:border-0"
              >
                <span className="w-4 shrink-0 text-[16px] font-bold text-[#cfccc0]">{i + 1}</span>
                <div className="min-w-0 max-w-[640px]">
                  <p className="text-sm font-semibold">{item.title}</p>
                  <p className="mt-1 text-sm leading-relaxed text-ink-muted">{item.why}</p>
                  <p className="mt-1.5 text-sm leading-relaxed">{item.how}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      )}

      {review.bullet_rewrites.length > 0 && (
        <div className="mt-7">
          <h3 className="text-[13.5px] font-semibold text-ink-text">Rewrites</h3>
          <div className="mt-2 max-w-[680px] space-y-5">
            {review.bullet_rewrites.map((rewrite, i) => (
              <div key={i}>
                <p className="font-mono text-[13px] leading-relaxed text-ink-dim line-through">
                  {rewrite.original}
                </p>
                <p className="mt-1.5 font-mono text-[13px] leading-relaxed text-ink-text">
                  {rewrite.improved}
                </p>
                <p className="mt-1.5 text-[13px] leading-relaxed text-ink-muted">
                  {rewrite.rationale}
                </p>
              </div>
            ))}
          </div>
          <p className="mt-4 max-w-[640px] text-[13px] leading-relaxed text-ink-dim">
            Placeholders like [X%] mark where your own number belongs. Fill them in. Never ship
            a figure you can't defend.
          </p>
        </div>
      )}

      {review.tailoring_notes.length > 0 && (
        <div className="mt-7">
          <h3 className="text-[13.5px] font-semibold text-ink-text">Tailoring to this job</h3>
          <ul className="mt-2 max-w-[640px] space-y-2 text-sm leading-relaxed text-ink-muted">
            {review.tailoring_notes.map((note, i) => (
              <li key={i}>{note}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

/* -------------------------------------------------------- parsed record */
export function SnapshotPanel({ snapshot }: { snapshot: ParsedSnapshot }) {
  const { contact } = snapshot
  const rows: [string, string][] = [
    ['Name', contact.name ?? 'not found'],
    ['Email', contact.emails[0] ?? 'not found'],
    ['Phone', contact.phones[0] ?? 'not found'],
    ['Location', contact.location ?? 'not found'],
    ['LinkedIn', contact.linkedin ?? 'not found'],
    ['Sections', snapshot.detected_sections.join(', ') || 'none recognised'],
    ['Bullets', String(snapshot.bullet_count)],
    ['Experience', `${snapshot.experience_years} years`],
    ['Length', `${snapshot.word_count} words · ${snapshot.page_count} page(s)`],
  ]

  return (
    <section className="mt-9 border-t border-ink-line pt-6" aria-label="What the parser found">
      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
        <h2 className="section-title">Parsed record</h2>
        <span className="text-[13px] text-ink-dim">
          if anything here is wrong, a real screening system gets it wrong too
        </span>
      </div>
      <dl className="mt-4 grid gap-x-10 gap-y-3.5 sm:grid-cols-2 lg:grid-cols-3">
        {rows.map(([label, value]) => (
          <div key={label}>
            <dt className="text-[12.5px] text-ink-dim">{label}</dt>
            <dd
              className={`mt-0.5 font-mono text-[13px] [overflow-wrap:anywhere] ${
                value === 'not found' || value === 'none recognised' ? 'text-[color:var(--color-mark-critical)]' : 'text-ink-text'
              }`}
            >
              {value}
            </dd>
          </div>
        ))}
      </dl>

      {snapshot.gaps.length > 0 && (
        <p className="mt-4 font-mono text-[12.5px] text-ink-muted">
          Timeline gaps:{' '}
          {snapshot.gaps.map((gap, i) => (
            <span key={i}>
              {i > 0 && ' · '}
              {gap.from} to {gap.to} ({gap.months} {gap.months === 1 ? 'month' : 'months'})
            </span>
          ))}
        </p>
      )}
    </section>
  )
}
