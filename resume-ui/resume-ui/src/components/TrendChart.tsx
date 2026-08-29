import { useState } from 'react'
import type { CSSProperties } from 'react'
import { useNavigate } from 'react-router-dom'
import { bandColor } from './Verdict'

/**
 * Score over time: one series, so no legend — the panel title names it.
 * Line and dots stay in a neutral ink; only the latest point wears its band
 * color, and every value label uses text tokens rather than the series color.
 */
export interface TrendPoint {
  id: string
  score: number
  date: string
  label: string
}

const W = 640
const H = 180
const PAD = { l: 38, r: 20, t: 22, b: 30 }

export function TrendChart({ points }: { points: TrendPoint[] }) {
  const navigate = useNavigate()
  const [hover, setHover] = useState<number | null>(null)
  if (points.length < 2) return null

  const x = (index: number) => PAD.l + (index * (W - PAD.l - PAD.r)) / (points.length - 1)
  const y = (score: number) => PAD.t + ((100 - score) * (H - PAD.t - PAD.b)) / 100
  const path = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)},${y(p.score).toFixed(1)}`)
    .join(' ')
  const last = points.length - 1
  const formatDate = (iso: string) =>
    new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })

  const active = hover ?? last
  const tooltipX = Math.min(Math.max(x(active), PAD.l + 58), W - PAD.r - 58)

  return (
    <figure className="m-0">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="block w-full"
        role="img"
        aria-label={`Score trend across ${points.length} reviews, from ${points[0].score} to ${points[last].score} out of 100.`}
      >
        {/* recessive grid */}
        {[0, 25, 50, 75, 100].map((tick) => (
          <line
            key={tick}
            x1={PAD.l}
            x2={W - PAD.r}
            y1={y(tick)}
            y2={y(tick)}
            stroke="var(--color-ink-line)"
            strokeWidth="1"
          />
        ))}
        {[0, 50, 100].map((tick) => (
          <text
            key={tick}
            x={PAD.l - 8}
            y={y(tick) + 3.5}
            textAnchor="end"
            fontSize="10"
            fontFamily="var(--font-mono)"
            fill="var(--color-ink-muted)"
          >
            {tick}
          </text>
        ))}
        {/* axis dates: ends only */}
        <text x={x(0)} y={H - 8} textAnchor="start" fontSize="10" fontFamily="var(--font-mono)" fill="var(--color-ink-muted)">
          {formatDate(points[0].date)}
        </text>
        <text x={x(last)} y={H - 8} textAnchor="end" fontSize="10" fontFamily="var(--font-mono)" fill="var(--color-ink-muted)">
          {formatDate(points[last].date)}
        </text>

        <path d={path} pathLength={1} className="chart-draw" fill="none" stroke="var(--color-ink-muted)" strokeWidth="1.5" strokeLinejoin="round" />

        {points.map((point, index) => {
          const isLast = index === last
          const isHover = hover === index
          return (
            <g key={point.id}>
              <circle
                className="chart-dot"
                style={{ '--i': index } as CSSProperties}
                cx={x(index)}
                cy={y(point.score)}
                r={isLast ? 4.5 : 3.5}
                fill={isLast ? bandColor(point.score) : 'var(--color-ink-raised)'}
                stroke={isHover ? 'var(--color-ink-text)' : 'var(--color-ink-muted)'}
                strokeWidth="1.5"
              />
              {/* hit target wider than the mark */}
              <rect
                x={x(index) - (W - PAD.l - PAD.r) / (points.length - 1) / 2}
                y={PAD.t}
                width={(W - PAD.l - PAD.r) / (points.length - 1)}
                height={H - PAD.t - PAD.b}
                fill="transparent"
                className="cursor-pointer"
                onMouseEnter={() => setHover(index)}
                onMouseLeave={() => setHover(null)}
                onClick={() => navigate(`/analyses/${point.id}`)}
              />
            </g>
          )
        })}

        {/* direct labels on the ends; hover replaces them with the active point */}
        {hover === null && (
          <text
            x={x(0)}
            y={y(points[0].score) - 10}
            textAnchor="middle"
            fontSize="11"
            fontFamily="var(--font-mono)"
            fill="var(--color-ink-muted)"
          >
            {Math.round(points[0].score)}
          </text>
        )}
        <g pointerEvents="none">
          <rect
            x={tooltipX - 56}
            y={Math.max(2, y(points[active].score) - 34)}
            width="112"
            height="20"
            rx="6"
            fill="var(--color-ink)"
            stroke="var(--color-ink-line)"
          />
          <text
            x={tooltipX}
            y={Math.max(2, y(points[active].score) - 34) + 14}
            textAnchor="middle"
            fontSize="10.5"
            fontFamily="var(--font-mono)"
            fill="var(--color-ink-text)"
          >
            {Math.round(points[active].score)} · {formatDate(points[active].date)}
          </text>
        </g>
      </svg>

      {/* table view for screen readers */}
      <figcaption className="sr-only">
        <ul>
          {points.map((point) => (
            <li key={point.id}>
              {formatDate(point.date)}, {point.label}: {Math.round(point.score)} out of 100
            </li>
          ))}
        </ul>
      </figcaption>
    </figure>
  )
}
