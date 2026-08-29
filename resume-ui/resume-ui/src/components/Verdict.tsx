import type { CSSProperties } from 'react'
import { Link } from 'react-router-dom'
import { useCountUp } from '../lib/useCountUp'
import type { CategoryScore, CompareResult } from '../types'

const BAND_COPY: Record<string, string> = {
  excellent: 'Ready to send.',
  good: 'A few clear fixes remain.',
  fair: 'Costing you interviews.',
  needs_work: 'Needs real revision.',
  poor: 'Start again on the writing.',
}

const SHORT_LABELS: Record<string, string> = {
  contact: 'Contact',
  structure: 'Structure',
  impact: 'Impact',
  ats: 'ATS',
  formatting: 'Formatting',
  keywords: 'Job match',
}

export function bandColor(score: number): string {
  if (score >= 85) return 'var(--color-mark-positive)'
  if (score >= 55) return 'var(--color-mark-warning)'
  return 'var(--color-mark-critical)'
}

function valueColor(score: number): string | undefined {
  if (score < 55) return 'var(--color-mark-critical)'
  if (score < 85) return 'var(--color-mark-warning)'
  return undefined
}

/**
 * The scoreboard band: the page's focal point. A strong rule, the score as a
 * large numeral colored by its band, the verdict beside it, and the category
 * readings as one inline stat line — no meters, no boxes.
 */
export function Scoreboard({
  score,
  band,
  verdict,
  categories,
  compare,
}: {
  score: number
  band: string | null
  verdict: string | null
  categories: CategoryScore[]
  compare: CompareResult | null
}) {
  const applicable = categories.filter((c) => c.applicable)
  const skipped = categories.filter((c) => !c.applicable)
  const delta = compare?.delta.overall
  const shown = useCountUp(score)

  return (
    <section
      className="mt-5 border-t border-ink-text border-b border-b-ink-line pt-6 pb-6"
      aria-label="Overall score"
    >
      <div className="flex flex-wrap items-start gap-x-10 gap-y-4">
        <div className="flex items-baseline gap-2">
          <span
            className="text-[56px] leading-[0.9] font-extrabold tracking-[-0.03em] tabular-nums sm:text-[64px]"
            style={{ color: bandColor(score) }}
            aria-label={`${score.toFixed(1)} out of 100`}
          >
            {shown.toFixed(1)}
          </span>
          <span className="font-mono text-sm text-ink-dim">/100</span>
        </div>
        <div className="rise min-w-0 pt-1" style={{ '--i': 2 } as CSSProperties}>
          <p className="text-lg font-bold tracking-tight">
            {band ? (BAND_COPY[band] ?? band) : 'Scored.'}
          </p>
          {verdict && (
            <p className="mt-1 max-w-[520px] text-sm leading-relaxed text-ink-muted">{verdict}</p>
          )}
        </div>
      </div>

      <div className="mt-6 grid grid-cols-2 gap-x-10 gap-y-4 sm:grid-cols-3">
        {applicable.map((category, index) => (
          <div key={category.category} className="min-w-0">
            <div className="flex items-baseline justify-between gap-3 text-[13px]">
              <span className="text-ink-muted">
                {SHORT_LABELS[category.category] ?? category.label}
              </span>
              <span
                className="font-mono font-medium text-ink-text tabular-nums"
                style={{ color: valueColor(category.score) }}
              >
                {Math.round(category.score)}
              </span>
            </div>
            <div className="mt-1.5 h-[3px] overflow-hidden rounded-full bg-[#eceadf]">
              <div
                className="bar-fill h-full rounded-full"
                style={
                  {
                    width: `${Math.max(2, category.score)}%`,
                    backgroundColor: valueColor(category.score) ?? 'var(--color-ink-text)',
                    '--i': index,
                  } as CSSProperties
                }
              />
            </div>
          </div>
        ))}
        {skipped.map((category) => (
          <div key={category.category} className="min-w-0">
            <div className="flex items-baseline justify-between gap-3 text-[13px]">
              <span className="text-ink-muted">
                {SHORT_LABELS[category.category] ?? category.label}
              </span>
              <span className="text-[12.5px] text-ink-dim italic">not scored</span>
            </div>
            <div className="mt-1.5 h-[3px] rounded-full bg-[#eceadf]" />
          </div>
        ))}
      </div>

      {compare && (
        <p className="mt-4 text-[13.5px]">
          <span className="text-ink-muted">
            Since last review{' '}
            <span
              className="font-mono font-medium tabular-nums"
              style={{
                color:
                  delta && delta > 0
                    ? 'var(--color-mark-positive)'
                    : delta && delta < 0
                      ? 'var(--color-mark-critical)'
                      : 'var(--color-ink-text)',
              }}
            >
              {delta && delta > 0 ? `+${delta}` : (delta ?? '±0')}
            </span>
            {compare.delta.resolved.length > 0 && (
              <span
                className="text-[color:var(--color-mark-positive)]"
                title={compare.delta.resolved.map((f) => f.title).join('\n')}
              >
                {' '}
                · {compare.delta.resolved.length} resolved
              </span>
            )}{' '}
            ·{' '}
            <Link to={`/analyses/${compare.baseline.id}`} className="font-medium text-brand">
              view previous
            </Link>
          </span>
        </p>
      )}
    </section>
  )
}
