import type { CSSProperties } from 'react'

/**
 * Drawn pieces in the green-ink style: 1.5px strokes, the warm ink palette,
 * severity colors only where they mean something. All decorative SVGs are
 * aria-hidden; the surrounding text carries the meaning.
 */

/** A resume sheet being read: a green scan line sweeps the page. */
export function ScanIllustration({ width = 88 }: { width?: number }) {
  return (
    <svg
      width={width}
      viewBox="0 0 88 112"
      fill="none"
      aria-hidden="true"
      className="shrink-0"
    >
      <rect x="1" y="1" width="86" height="110" rx="5" fill="#ffffff" stroke="var(--color-ink-line)" strokeWidth="1.5" />
      <rect x="12" y="13" width="34" height="5" rx="2.5" fill="var(--color-ink-text)" opacity="0.8" />
      <rect x="12" y="25" width="62" height="3.5" rx="1.75" fill="#d9d6ca" />
      <rect x="12" y="33" width="54" height="3.5" rx="1.75" fill="#d9d6ca" />
      <rect x="12" y="45" width="24" height="4" rx="2" fill="var(--color-ink-muted)" />
      <rect x="12" y="55" width="64" height="3.5" rx="1.75" fill="#d9d6ca" />
      <rect x="12" y="63" width="46" height="3.5" rx="1.75" fill="var(--color-mark-warning)" opacity="0.5" />
      <rect x="12" y="71" width="58" height="3.5" rx="1.75" fill="#d9d6ca" />
      <rect x="12" y="83" width="24" height="4" rx="2" fill="var(--color-ink-muted)" />
      <rect x="12" y="93" width="50" height="3.5" rx="1.75" fill="#d9d6ca" />
      <g className="scan-line">
        <rect x="3" y="4" width="82" height="16" fill="var(--color-brand)" opacity="0.07" />
        <rect x="3" y="19" width="82" height="1.5" fill="var(--color-brand)" />
      </g>
    </svg>
  )
}

/** First-run empty state: a reviewed sheet with the proof mark drawn in. */
export function EmptyResumeArt() {
  return (
    <svg width="104" viewBox="0 0 104 128" fill="none" aria-hidden="true" className="mx-auto">
      <rect x="1.5" y="1.5" width="101" height="125" rx="6" fill="#ffffff" stroke="var(--color-ink-line)" strokeWidth="1.5" />
      <rect x="14" y="16" width="40" height="5.5" rx="2.75" fill="var(--color-ink-text)" opacity="0.8" />
      <rect x="14" y="30" width="74" height="4" rx="2" fill="#d9d6ca" />
      <rect x="14" y="39" width="64" height="4" rx="2" fill="#d9d6ca" />
      <rect x="14" y="55" width="28" height="4.5" rx="2.25" fill="var(--color-ink-muted)" />
      <rect x="14" y="66" width="74" height="4" rx="2" fill="#d9d6ca" />
      <rect x="14" y="75" width="52" height="4" rx="2" fill="var(--color-mark-warning)" opacity="0.5" />
      <rect x="14" y="84" width="68" height="4" rx="2" fill="#d9d6ca" />
      <rect x="14" y="100" width="42" height="4" rx="2" fill="#d9d6ca" />
      <circle cx="82" cy="104" r="13" fill="var(--color-tint-positive)" stroke="var(--color-brand)" strokeWidth="1.5" />
      <path
        d="M76 104.5l4 4 8-8.5"
        stroke="var(--color-brand)"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        pathLength={1}
        className="chart-draw"
      />
    </svg>
  )
}

/** Job-match coverage as a small ring that draws to its value. */
export function CoverageRing({ coverage, size = 18 }: { coverage: number; size?: number }) {
  const r = (size - 3) / 2
  const c = 2 * Math.PI * r
  const clamped = Math.min(1, Math.max(0, coverage))
  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      aria-hidden="true"
      className="inline-block align-[-3px]"
    >
      <circle cx={size / 2} cy={size / 2} r={r} stroke="var(--color-ink-line)" strokeWidth="3" fill="none" />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        stroke="var(--color-brand)"
        strokeWidth="3"
        fill="none"
        strokeLinecap="round"
        className="ring-draw"
        style={
          {
            '--ring-c': `${c}`,
            strokeDasharray: c,
            strokeDashoffset: c * (1 - clamped),
            transform: 'rotate(-90deg)',
            transformOrigin: 'center',
          } as CSSProperties
        }
      />
    </svg>
  )
}
