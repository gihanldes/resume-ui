import { useMemo, useRef, useEffect, useState } from 'react'
import type { CSSProperties } from 'react'
import type { Finding, Severity } from '../types'
import { MARK } from './ui'

/**
 * The signature panel: the resume as source, line-numbered, with every
 * flagged span marked in place. Collapsed by default — the flags are the
 * point, so "Next flag" walks through them and expanding is one click.
 */

interface Segment {
  text: string
  severity: Severity | null
  findingId: string | null
}

/** Longest evidence first, so a broad quote can't pre-empt a specific one. */
function collectEvidence(findings: Finding[]) {
  const items: { text: string; severity: Severity; findingId: string }[] = []
  for (const finding of findings) {
    if (finding.severity === 'positive') continue
    for (const raw of finding.evidence) {
      const text = raw.trim()
      // Single words and very short fragments would mark half the document.
      if (text.length < 4) continue
      items.push({ text, severity: finding.severity, findingId: finding.id })
    }
  }
  return items.sort((a, b) => b.text.length - a.text.length)
}

function buildSegments(source: string, findings: Finding[]): Segment[] {
  const evidence = collectEvidence(findings)
  if (!evidence.length) return [{ text: source, severity: null, findingId: null }]

  const lower = source.toLowerCase()
  // claimed[i] holds the evidence index owning character i, or -1.
  const claimed = new Int32Array(source.length).fill(-1)

  evidence.forEach((item, index) => {
    const needle = item.text.toLowerCase()
    let from = 0
    while (from <= lower.length - needle.length) {
      const at = lower.indexOf(needle, from)
      if (at === -1) break
      let free = true
      for (let i = at; i < at + needle.length; i += 1) {
        if (claimed[i] !== -1) {
          free = false
          break
        }
      }
      if (free) claimed.fill(index, at, at + needle.length)
      from = at + Math.max(1, needle.length)
    }
  })

  const segments: Segment[] = []
  let cursor = 0
  while (cursor < source.length) {
    const owner = claimed[cursor]
    let end = cursor + 1
    while (end < source.length && claimed[end] === owner) end += 1
    segments.push({
      text: source.slice(cursor, end),
      severity: owner === -1 ? null : evidence[owner].severity,
      findingId: owner === -1 ? null : evidence[owner].findingId,
    })
    cursor = end
  }
  return segments
}

/** Split marked segments into per-line runs so each line can carry a number. */
function buildLines(segments: Segment[]): Segment[][] {
  const lines: Segment[][] = [[]]
  for (const segment of segments) {
    const parts = segment.text.split('\n')
    parts.forEach((part, index) => {
      if (index > 0) lines.push([])
      if (part) lines[lines.length - 1].push({ ...segment, text: part })
    })
  }
  return lines
}

export function ProofSheet({
  text,
  findings,
  activeFindingId,
  onSelectFinding,
}: {
  text: string
  findings: Finding[]
  activeFindingId: string | null
  onSelectFinding: (id: string | null) => void
}) {
  const segments = useMemo(() => buildSegments(text, findings), [text, findings])
  const lines = useMemo(() => buildLines(segments), [segments])
  const containerRef = useRef<HTMLDivElement>(null)
  const flagIndexRef = useRef(-1)
  const [expanded, setExpanded] = useState(false)

  // A selected finding always opens the source so its marks are reachable.
  useEffect(() => {
    if (activeFindingId) setExpanded(true)
  }, [activeFindingId])

  // Bring the first mark for the selected finding into view once visible.
  useEffect(() => {
    if (!activeFindingId || !expanded || !containerRef.current) return
    const frame = requestAnimationFrame(() => {
      const target = containerRef.current?.querySelector(
        `[data-finding="${CSS.escape(activeFindingId)}"]`,
      )
      target?.scrollIntoView({ block: 'center', behavior: 'smooth' })
    })
    return () => cancelAnimationFrame(frame)
  }, [activeFindingId, expanded])

  const flaggedCount = segments.filter((s) => s.findingId).length

  function nextFlag() {
    setExpanded(true)
    requestAnimationFrame(() => {
      const marks = containerRef.current?.querySelectorAll<HTMLElement>('mark[data-finding]')
      if (!marks || marks.length === 0) return
      flagIndexRef.current = (flagIndexRef.current + 1) % marks.length
      const mark = marks[flagIndexRef.current]
      onSelectFinding(mark.dataset.finding ?? null)
      mark.scrollIntoView({ block: 'center', behavior: 'smooth' })
    })
  }

  return (
    <section aria-label="Resume as the parser reads it">
      <header className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
        <h2 className="section-title">Source</h2>
        <span className="text-[13px] text-ink-muted">
          what a screening system reads ·{' '}
          <span className="font-mono">{flaggedCount} span{flaggedCount === 1 ? '' : 's'} flagged</span>
        </span>
        <div className="ml-auto flex items-baseline gap-4.5">
          {flaggedCount > 0 && (
            <button
              type="button"
              onClick={nextFlag}
              className="text-sm font-medium text-brand hover:underline"
            >
              Next flag
            </button>
          )}
          <button
            type="button"
            onClick={() => setExpanded((value) => !value)}
            aria-expanded={expanded}
            className="text-sm font-medium text-brand hover:underline"
          >
            {expanded ? 'Collapse' : `Expand · ${lines.length} lines`}
          </button>
        </div>
      </header>

      <div className="well relative mt-3.5">
        <div
          ref={containerRef}
          className={`px-6 py-5 ${
            expanded ? 'max-h-[34rem] overflow-y-auto' : 'max-h-[16rem] overflow-hidden'
          }`}
          style={{ scrollbarWidth: 'thin' }}
        >
          <div className="font-mono text-[13px] leading-[25px] text-ink-text">
            {lines.map((pieces, lineIndex) => (
              <div key={lineIndex} className="grid grid-cols-[2rem_1fr] gap-x-4">
                <span
                  className="text-right font-mono text-[11px] leading-[25px] text-[#b9b6aa] select-none"
                  aria-hidden="true"
                >
                  {String(lineIndex + 1).padStart(2, '0')}
                </span>
                <span className="break-words whitespace-pre-wrap">
                  {pieces.length === 0
                    ? ' '
                    : pieces.map((piece, pieceIndex) => {
                        if (!piece.severity || !piece.findingId) {
                          return <span key={pieceIndex}>{piece.text}</span>
                        }
                        const active = piece.findingId === activeFindingId
                        const color = MARK[piece.severity].color
                        return (
                          <mark
                            key={pieceIndex}
                            data-finding={piece.findingId}
                            data-active={active || undefined}
                            onClick={() => onSelectFinding(active ? null : piece.findingId)}
                            className="cursor-pointer rounded-[2px] transition-colors"
                            style={
                              {
                                background: `color-mix(in srgb, ${color} ${active ? 30 : 14}%, transparent)`,
                                color: 'inherit',
                                boxShadow: `inset 0 -2px 0 0 ${color}`,
                                '--mark-c': color,
                              } as CSSProperties
                            }
                            title={MARK[piece.severity].label}
                          >
                            {piece.text}
                          </mark>
                        )
                      })}
                </span>
              </div>
            ))}
          </div>
        </div>

        {!expanded && (
          <button
            type="button"
            onClick={() => setExpanded(true)}
            className="absolute inset-x-0 bottom-0 flex h-16 items-end justify-center rounded-b-md pb-3 text-[13px] font-medium text-brand transition-colors hover:text-brand-deep"
            style={{
              background: 'linear-gradient(to bottom, rgba(244,242,236,0), #f4f2ec 70%)',
            }}
          >
            Show all {lines.length} lines
          </button>
        )}
      </div>
    </section>
  )
}
