import { useState } from 'react'
import type { CSSProperties } from 'react'
import { sectionLabel } from '../lib/sections'
import type { Finding, Severity } from '../types'
import { Mark, MARK } from './ui'

const ORDER: Severity[] = ['critical', 'warning', 'suggestion', 'positive']

function penaltyColor(finding: Finding): string {
  if (finding.severity === 'critical' || finding.severity === 'warning') {
    return MARK[finding.severity].color
  }
  return 'var(--color-ink-muted)'
}

function FindingRow({
  finding,
  active,
  onSelect,
}: {
  finding: Finding
  active: boolean
  onSelect: () => void
}) {
  return (
    <div className="border-b border-ink-faint last:border-0">
      <button
        type="button"
        onClick={onSelect}
        aria-expanded={active}
        className="flex w-full items-baseline gap-3.5 py-3.5 text-left transition-colors hover:bg-well/60"
      >
        <Mark severity={finding.severity} />
        <span
          className={`min-w-0 flex-1 text-[14.5px] text-ink-text ${active ? 'font-semibold' : 'font-medium'}`}
        >
          {finding.title}
        </span>
        <span className="hidden shrink-0 text-[13px] text-ink-dim md:inline">
          {finding.category_label}
        </span>
        <span
          className="w-12 shrink-0 text-right font-mono text-[13px] tabular-nums"
          style={{ color: penaltyColor(finding) }}
        >
          {finding.severity === 'positive' ? (
            <span className="font-semibold text-[color:var(--color-mark-positive)]">pass</span>
          ) : (
            `-${finding.penalty.toFixed(1)}`
          )}
        </span>
      </button>

      {active && (
        <div className="pb-5 pl-7">
          <p className="max-w-[640px] text-sm leading-relaxed text-ink-muted">{finding.detail}</p>

          {finding.evidence.length > 0 && (
            <p className="mt-2.5 font-mono text-[12.5px] leading-relaxed text-ink-muted">
              {finding.evidence.map((item, index) => (
                <span key={index}>
                  {index > 0 && <span className="text-ink-dim"> · </span>}
                  “{item}”
                </span>
              ))}
            </p>
          )}

          {finding.fix && (
            <p className="mt-3 text-sm leading-relaxed">
              <span className="mr-2 font-semibold text-brand">Fix</span>
              {finding.fix}
            </p>
          )}
        </div>
      )}
    </div>
  )
}

export function FindingsList({
  findings,
  activeId,
  onSelect,
  sectionOrder = [],
}: {
  findings: Finding[]
  activeId: string | null
  onSelect: (id: string | null) => void
  /** The resume's own section order, so groups read in document order. */
  sectionOrder?: string[]
}) {
  const [filter, setFilter] = useState<Severity | 'all'>('all')

  const counts = ORDER.reduce<Record<string, number>>((acc, severity) => {
    acc[severity] = findings.filter((f) => f.severity === severity).length
    return acc
  }, {})

  const visible = filter === 'all' ? findings : findings.filter((f) => f.severity === filter)

  // Group by the resume's own sections; findings from analyses run before the
  // engine attributed sections all land in one group, which renders flat.
  const grouped = new Map<string, Finding[]>()
  for (const finding of visible) {
    const key = finding.section ?? 'document'
    const bucket = grouped.get(key)
    if (bucket) bucket.push(finding)
    else grouped.set(key, [finding])
  }
  const orderedKeys = [
    'document',
    ...sectionOrder.filter((name) => name !== 'document' && grouped.has(name)),
    ...[...grouped.keys()].filter((name) => name !== 'document' && !sectionOrder.includes(name)),
  ].filter((name, index, all) => grouped.has(name) && all.indexOf(name) === index)
  const isFlat = grouped.size === 1 && findings.every((f) => f.section === undefined)

  return (
    <div>
      <div className="flex flex-wrap items-baseline gap-x-6 gap-y-1 border-b border-ink-line">
        <h2 className="section-title pb-3">Findings</h2>
        <div className="flex flex-wrap gap-x-5 text-[13.5px]">
          <button
            type="button"
            onClick={() => setFilter('all')}
            className={`-mb-px pb-3 transition-colors ${
              filter === 'all'
                ? 'border-b-2 border-ink-text font-semibold text-ink-text'
                : 'text-ink-muted hover:text-ink-text'
            }`}
          >
            All {findings.length}
          </button>
          {ORDER.filter((severity) => counts[severity] > 0).map((severity) => (
            <button
              key={severity}
              type="button"
              onClick={() => setFilter(filter === severity ? 'all' : severity)}
              aria-pressed={filter === severity}
              className="-mb-px pb-3 transition-opacity"
              style={{
                color: MARK[severity].color,
                borderBottom: filter === severity ? `2px solid ${MARK[severity].color}` : undefined,
                fontWeight: filter === severity ? 600 : 400,
                opacity: filter === 'all' || filter === severity ? 1 : 0.5,
              }}
            >
              {MARK[severity].label} {counts[severity]}
            </button>
          ))}
        </div>
      </div>

      {isFlat ? (
        <div>
          {visible.map((finding, index) => (
            <div
              key={finding.id}
              className="rise"
              style={{ '--i': Math.min(index, 8) } as CSSProperties}
            >
              <FindingRow
                finding={finding}
                active={finding.id === activeId}
                onSelect={() => onSelect(finding.id === activeId ? null : finding.id)}
              />
            </div>
          ))}
        </div>
      ) : (
        orderedKeys.map((key, groupIndex) => (
          <div
            key={key}
            className="rise"
            style={{ '--i': Math.min(groupIndex, 8) } as CSSProperties}
          >
            <h3 className="flex items-baseline gap-2 pt-6 pb-1 text-[13px] font-bold tracking-wide text-ink-muted uppercase">
              {sectionLabel(key)}
              <span className="font-mono text-[11.5px] font-normal text-ink-dim normal-case">
                {grouped.get(key)!.length}
              </span>
            </h3>
            <div className="border-t border-ink-line">
              {grouped.get(key)!.map((finding) => (
                <FindingRow
                  key={finding.id}
                  finding={finding}
                  active={finding.id === activeId}
                  onSelect={() => onSelect(finding.id === activeId ? null : finding.id)}
                />
              ))}
            </div>
          </div>
        ))
      )}
    </div>
  )
}
