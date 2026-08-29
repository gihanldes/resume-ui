import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, TextareaHTMLAttributes } from 'react'
import type { Severity } from '../types'

/* ------------------------------------------------------------------ marks */
export const MARK: Record<
  Severity,
  { color: string; tint: string; glyph: string; label: string }
> = {
  critical: {
    color: 'var(--color-mark-critical)',
    tint: 'var(--color-tint-critical)',
    glyph: '×',
    label: 'Critical',
  },
  warning: {
    color: 'var(--color-mark-warning)',
    tint: 'var(--color-tint-warning)',
    glyph: '!',
    label: 'Warning',
  },
  suggestion: {
    color: 'var(--color-mark-suggestion)',
    tint: 'var(--color-tint-suggestion)',
    glyph: '~',
    label: 'Suggestion',
  },
  positive: {
    color: 'var(--color-mark-positive)',
    tint: 'var(--color-tint-positive)',
    glyph: '✓',
    label: 'Working well',
  },
}

/** Severity as a bare colored glyph — quiet, typographic, never a pill. */
export function Mark({ severity, size = 14 }: { severity: Severity; size?: number }) {
  const { color, glyph, label } = MARK[severity]
  return (
    <span
      role="img"
      aria-label={label}
      title={label}
      className="inline-block shrink-0 text-center font-mono font-semibold leading-none"
      style={{ color, fontSize: size, width: size }}
    >
      {glyph}
    </span>
  )
}

/** Severity as colored text with a count — used by filter tabs. */
export function SeverityBadge({ severity, count }: { severity: Severity; count?: number }) {
  const { color, label } = MARK[severity]
  return (
    <span className="text-[13.5px]" style={{ color }}>
      {label}
      {count !== undefined && ` ${count}`}
    </span>
  )
}

/* ---------------------------------------------------------------- buttons */
type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'ghost' | 'danger' | 'paper'
  loading?: boolean
}

export function Button({
  variant = 'primary',
  loading = false,
  disabled,
  children,
  className = '',
  ...rest
}: ButtonProps) {
  const base =
    'inline-flex items-center justify-center gap-2 rounded-md px-4 py-2.5 text-sm font-semibold ' +
    'transition-colors duration-150 active:translate-y-px disabled:cursor-not-allowed disabled:opacity-50'
  const variants = {
    primary: 'bg-brand text-[#fbfaf7] hover:bg-brand-deep',
    ghost: 'border border-ink-line bg-transparent text-ink-text hover:bg-well',
    danger:
      'border border-transparent bg-transparent font-medium text-[color:var(--color-mark-critical)] hover:bg-tint-critical',
    paper: 'bg-brand text-[#fbfaf7] hover:bg-brand-deep',
  }
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      className={`${base} ${variants[variant]} ${className}`}
    >
      {loading && <Spinner />}
      {children}
    </button>
  )
}

export function Spinner({ className = '' }: { className?: string }) {
  return (
    <svg
      className={`size-4 animate-spin ${className}`}
      viewBox="0 0 16 16"
      fill="none"
      aria-hidden="true"
    >
      <circle cx="8" cy="8" r="6.5" stroke="currentColor" strokeOpacity="0.25" strokeWidth="2" />
      <path d="M14.5 8A6.5 6.5 0 0 0 8 1.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

/* ----------------------------------------------------------------- fields */
export function Field({
  label,
  hint,
  error,
  children,
}: {
  label: string
  hint?: string
  error?: string
  children: ReactNode
}) {
  return (
    <label className="block">
      <span className="eyebrow block text-ink-muted">{label}</span>
      <div className="mt-1.5">{children}</div>
      {error ? (
        <span className="mt-1.5 block text-xs text-[color:var(--color-mark-critical)]">{error}</span>
      ) : hint ? (
        <span className="mt-1.5 block text-xs text-ink-muted">{hint}</span>
      ) : null}
    </label>
  )
}

const inputClass =
  'w-full rounded-md bg-white/60 px-3 py-2.5 text-sm text-ink-text placeholder:text-ink-dim ' +
  'border border-[#d5d2c6] transition-[border-color,box-shadow] outline-none ' +
  'focus:border-brand focus:shadow-[0_0_0_3px_rgba(42,93,70,0.14)]'

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={`${inputClass} ${props.className ?? ''}`} />
}

export function Textarea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      {...props}
      className={`${inputClass} resize-y leading-relaxed ${props.className ?? ''}`}
    />
  )
}

/* --------------------------------------------------------------- feedback */
export function Notice({
  tone = 'info',
  children,
}: {
  tone?: 'info' | 'error' | 'success'
  children: ReactNode
}) {
  const tones = {
    info: 'bg-well text-ink-muted',
    error: 'bg-tint-critical text-[color:var(--color-mark-critical)]',
    success: 'bg-tint-positive text-[color:var(--color-mark-positive)]',
  }
  return (
    <div
      className={`rounded-md px-3.5 py-2.5 text-[13.5px] leading-relaxed ${tones[tone]}`}
      role={tone === 'error' ? 'alert' : undefined}
    >
      {children}
    </div>
  )
}

export function Empty({
  title,
  children,
  action,
  art,
}: {
  title: string
  children: ReactNode
  action?: ReactNode
  art?: ReactNode
}) {
  return (
    <div className="border-t border-b border-ink-line px-6 py-12 text-center">
      {art && <div className="rise mb-6 flex justify-center">{art}</div>}
      <h3 className="text-lg text-ink-text">{title}</h3>
      <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-ink-muted">{children}</p>
      {action && <div className="mt-6 flex justify-center">{action}</div>}
    </div>
  )
}


/** Loading placeholder block. Compose into page-shaped skeletons. */
export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`animate-pulse rounded-md bg-[#edeae1] ${className}`} aria-hidden="true" />
}
