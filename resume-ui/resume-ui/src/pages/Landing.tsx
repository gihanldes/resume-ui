import { Link } from 'react-router-dom'
import { usePageTitle } from '../lib/usePageTitle'
import { useCountUp } from '../lib/useCountUp'

function SourceDemo() {
  const score = useCountUp(77.8, 800, 2600)
  const mark = (color: string, order: number) =>
    ({
      background: `color-mix(in srgb, ${color} 13%, transparent)`,
      boxShadow: `inset 0 -2px 0 0 ${color}`,
      borderRadius: '2px',
      color: 'inherit',
      '--i': order,
    }) as React.CSSProperties
  const lines: [string, React.ReactNode][] = [
    ['06', <>I am a <mark className="demo-mark" style={mark('#9c6b10', 0)}>hard working team player</mark> with a</>],
    ['07', <><mark className="demo-mark" style={mark('#9c6b10', 1)}>proven track record</mark>.</>],
    ['13', <>• <mark className="demo-mark" style={mark('#b3372b', 2)}>Responsible for</mark> the payouts pipeline</>],
    ['12', <>• Led migration, <mark className="demo-mark" style={mark('#2a5d46', 3)}>cutting p99 by 43%</mark></>],
  ]
  return (
    <div className="well rise px-6 py-5" aria-hidden="true" style={{ '--i': 2 } as React.CSSProperties}>
      <div className="flex items-baseline justify-between gap-4">
        <span className="text-[13px] font-semibold">Source: what a screening system reads</span>
        <span className="font-mono text-[11.5px] text-ink-dim">4 spans flagged</span>
      </div>
      <div className="mt-3 font-mono text-[13px] leading-[25px]">
        {lines.map(([number, content]) => (
          <div key={number} className="grid grid-cols-[1.75rem_1fr] gap-x-3">
            <span className="text-right text-[11px] leading-[25px] text-[#b9b6aa] select-none">
              {number}
            </span>
            <span className="truncate">{content}</span>
          </div>
        ))}
      </div>
      <div className="mt-4 flex items-baseline gap-2 border-t border-[#e3e0d5] pt-3.5">
        <span className="text-[40px] leading-none font-extrabold tracking-[-0.03em] text-[#9c6b10] tabular-nums">
          {score.toFixed(1)}
        </span>
        <span className="font-mono text-xs text-ink-dim">/100</span>
        <span className="ml-3 text-[13.5px] font-bold">A few clear fixes remain.</span>
      </div>
    </div>
  )
}

const FEATURES: [string, string][] = [
  [
    'A score you can check',
    'Six categories, each with a 100-point budget. Every deduction names the exact words that caused it. Nothing about the score is a guess.',
  ],
  [
    'See what the parser sees',
    'Your resume as plain source, line-numbered, with every flagged span marked in place. Columns, tables and images that break parsing get caught here.',
  ],
  [
    'Rewrites without invention',
    'The optional AI layer critiques the writing and rewrites weak bullets, but never fabricates your numbers. It leaves [X%] where yours belongs.',
  ],
]

export function Landing() {
  usePageTitle('')
  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-ink-line">
        <div className="mx-auto flex h-[60px] w-full max-w-[984px] items-center gap-8 px-5 sm:px-8">
          <span className="text-xl font-extrabold tracking-tight">
            Proof<span className="text-brand">.</span>
          </span>
          <div className="ml-auto flex items-center gap-5">
            <Link
              to="/signin"
              className="text-[13.5px] font-medium text-ink-text transition-colors hover:text-brand"
            >
              Sign in
            </Link>
            <Link
              to="/signup"
              className="rounded-md bg-brand px-3.5 py-2 text-[13.5px] font-semibold text-[#fbfaf7] transition-colors hover:bg-brand-deep"
            >
              Create an account
            </Link>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-[984px] flex-1 px-5 sm:px-8">
        <section className="grid items-center gap-12 py-14 lg:grid-cols-[1.05fr_1fr] lg:py-20">
          <div>
            <p className="rise mb-3 text-[13px] font-medium text-ink-muted">
              This app was built for academic purposes.
            </p>
            <h1 className="rise text-[34px] leading-[1.12] font-bold tracking-tight sm:text-[42px]">
              Your resume is screened by software before a person ever reads it. See that screen
              first.
            </h1>
            <p className="rise mt-5 max-w-lg text-[15px] leading-relaxed text-ink-muted" style={{ '--i': 1 } as React.CSSProperties}>
              Proof scores your resume with a deterministic rule engine: six categories, every
              deduction tied to the exact words that caused it. Then it shows you the plain text
              a tracking system actually parses.
            </p>
            <div className="rise mt-7 flex flex-wrap items-center gap-5" style={{ '--i': 2 } as React.CSSProperties}>
              <Link
                to="/signup"
                className="rounded-md bg-brand px-5 py-3 text-sm font-semibold text-[#fbfaf7] transition-colors hover:bg-brand-deep"
              >
                Create an account
              </Link>
              <Link to="/signin" className="text-sm font-medium text-brand hover:underline">
                Sign in
              </Link>
            </div>
            <p className="rise mt-6 text-[13px] text-ink-dim" style={{ '--i': 3 } as React.CSSProperties}>
              PDF, DOCX or TXT · deterministic score · AI rewrites optional
            </p>
          </div>

          <SourceDemo />
        </section>

        <section className="grid gap-x-10 gap-y-8 border-t border-ink-text py-12 sm:grid-cols-3">
          {FEATURES.map(([title, body], index) => (
            <div key={title}>
              <p className="text-[19px] font-bold text-[#cfccc0]">{index + 1}</p>
              <h2 className="mt-2 text-[15px] font-bold">{title}</h2>
              <p className="mt-1.5 text-[13.5px] leading-relaxed text-ink-muted">{body}</p>
            </div>
          ))}
        </section>
      </main>

      <footer className="border-t border-ink-line">
        <div className="mx-auto flex max-w-[984px] flex-wrap items-baseline gap-x-8 gap-y-1 px-5 py-4 text-[12.5px] text-ink-dim sm:px-8">
          <span className="min-w-0 flex-1 basis-72">
            Scores are deterministic and auditable. The optional AI layer never invents your
            numbers.
          </span>
          <span className="flex gap-5">
            <Link to="/how-it-works" className="transition-colors hover:text-ink-text">How it works</Link>
            <Link to="/terms" className="transition-colors hover:text-ink-text">Terms</Link>
            <Link to="/privacy" className="transition-colors hover:text-ink-text">Privacy</Link>
          </span>
        </div>
      </footer>
    </div>
  )
}
