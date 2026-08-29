import { Link } from 'react-router-dom'
import { ScanIllustration } from '../components/art'
import { usePageTitle } from '../lib/usePageTitle'

export function NotFound() {
  usePageTitle('Not found')
  return (
    <div className="mx-auto max-w-md px-6 py-14 text-center">
      <div className="rise flex justify-center"><ScanIllustration width={64} /></div>
      <p className="mt-6 font-mono text-[13px] text-ink-dim">404</p>
      <h1 className="mt-1 text-[24px] leading-tight">This page didn't parse.</h1>
      <p className="mt-2 text-sm leading-relaxed text-ink-muted">
        The link may be stale, or what it pointed at was deleted.
      </p>
      <Link to="/" className="mt-6 inline-block text-sm font-medium text-brand hover:underline">
        Back to Home
      </Link>
    </div>
  )
}
