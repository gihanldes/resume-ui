import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { usePageTitle } from '../lib/usePageTitle'

/** Static pages render inside the app Layout when signed in; signed out they
 *  bring their own minimal chrome. */
function StaticShell({ title, children }: { title: string; children: ReactNode }) {
  const { user } = useAuth()
  usePageTitle(title)

  const body = (
    <article className="mx-auto max-w-[720px]">
      <h1 className="text-[26px] leading-tight">{title}</h1>
      <div className="mt-5 space-y-4 text-[14.5px] leading-relaxed text-ink-muted [&_h2]:mt-7 [&_h2]:text-[15px] [&_h2]:font-bold [&_h2]:text-ink-text">
        {children}
      </div>
    </article>
  )

  if (user) return body

  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-ink-line">
        <div className="mx-auto flex h-[60px] w-full max-w-[984px] items-center gap-6 px-5 sm:px-8">
          <Link to="/" className="text-xl font-extrabold tracking-tight text-ink-text">
            Proof<span className="text-brand">.</span>
          </Link>
          <Link to="/signin" className="ml-auto text-sm font-medium text-brand hover:underline">
            Sign in
          </Link>
        </div>
      </header>
      <main className="mx-auto w-full max-w-[984px] flex-1 px-5 py-10 sm:px-8">{body}</main>
      <footer className="border-t border-ink-line">
        <div className="mx-auto flex max-w-[984px] gap-5 px-5 py-4 text-[12.5px] text-ink-dim sm:px-8">
          <Link to="/how-it-works" className="transition-colors hover:text-ink-text">How it works</Link>
          <Link to="/terms" className="transition-colors hover:text-ink-text">Terms</Link>
          <Link to="/privacy" className="transition-colors hover:text-ink-text">Privacy</Link>
        </div>
      </footer>
    </div>
  )
}

const CATEGORIES: [string, number, string][] = [
  ['Contact', 10, 'Name, email, phone, location and profile links are present and machine-readable.'],
  ['Structure', 15, 'The expected sections exist, are findable, and actually have content under them.'],
  ['Impact', 25, 'Bullets are quantified achievements with strong openers, not duty descriptions.'],
  ['ATS', 20, 'The file survives automated parsing: no lost text, columns, tables or image-only content.'],
  ['Formatting', 15, 'Length, dates, tense and consistency hold up to a six-second human skim.'],
  ['Job match', 15, 'How much of a pasted job description is genuinely evidenced. Only runs with one.'],
]

export function HowItWorks() {
  return (
    <StaticShell title="How scoring works">
      <p>
        Proof scores with a deterministic rule engine. The same resume always gets the same
        score, and every deduction names the exact words that caused it. Nothing about the
        number is a guess, which means you can audit it, disagree with it, and fix it.
      </p>
      <h2>Six categories, 100 points each</h2>
      <div>
        {CATEGORIES.map(([name, weight, description]) => (
          <div key={name} className="flex gap-5 border-b border-ink-faint py-3 last:border-0">
            <span className="w-24 shrink-0 font-semibold text-ink-text">{name}</span>
            <span className="w-10 shrink-0 font-mono text-[13px] text-ink-text">{weight}%</span>
            <span className="min-w-0">{description}</span>
          </div>
        ))}
      </div>
      <p>
        The overall score is the weighted blend of the six. Each finding carries the points it
        costs, so the priority list is simply the most expensive problems first.
      </p>
      <h2>What the AI layer does</h2>
      <p>
        The optional AI review critiques the writing and rewrites weak bullets. It never
        changes the score and never invents numbers: where a metric belongs, it leaves a
        placeholder like [X%] for your real figure.
      </p>
      <h2>What Proof reads</h2>
      <p>
        Exactly what a screening system reads: the plain text extracted from your file. The
        Source view shows that text line by line, so when a layout hides content from the
        parser, you see it disappear too.
      </p>
    </StaticShell>
  )
}

export function Terms() {
  return (
    <StaticShell title="Terms of service">
      <p className="font-medium text-ink-text">
        Draft. This is a plain-English summary written for a personal deployment of Proof and
        is not yet legal advice.
      </p>
      <h2>The service</h2>
      <p>
        Proof analyses resumes you upload and reports a score with suggested fixes. Scores are
        automated guidance, not hiring decisions, and no outcome is guaranteed.
      </p>
      <h2>Your account</h2>
      <p>
        You are responsible for your credentials and for what you upload. Upload only resumes
        you have the right to share.
      </p>
      <h2>Your content</h2>
      <p>
        Resumes and reviews stay yours. They are stored so you can revisit them and are never
        sold or shared with third parties. Deleting a resume, a review, or your account removes
        the underlying data permanently.
      </p>
      <h2>Availability</h2>
      <p>
        The service is provided as is, without warranty. It may change or pause without notice.
      </p>
    </StaticShell>
  )
}

export function Privacy() {
  return (
    <StaticShell title="Privacy">
      <p className="font-medium text-ink-text">
        Draft. This is a plain-English summary written for a personal deployment of Proof and
        is not yet legal advice.
      </p>
      <h2>What is stored</h2>
      <p>
        Your email, a hash of your password, resumes you upload, and the reviews generated from
        them. Resumes are personal data and are treated that way.
      </p>
      <h2>What it is used for</h2>
      <p>
        Only to run your reviews and show you your history. No advertising, no selling data, no
        profiling beyond the review you asked for.
      </p>
      <h2>The AI layer</h2>
      <p>
        With the AI review enabled, resume text is sent to the configured model provider to
        generate the critique. Turn the toggle off to keep a review fully local to the rule
        engine.
      </p>
      <h2>Deletion</h2>
      <p>
        Deleting your account deletes every resume, review and session that belongs to it,
        immediately and permanently.
      </p>
      <h2>Contact</h2>
      <p>Questions about your data: contact the operator of this deployment by email.</p>
    </StaticShell>
  )
}
