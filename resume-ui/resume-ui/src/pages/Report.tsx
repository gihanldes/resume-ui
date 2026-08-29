import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { sectionLabel } from '../lib/sections'
import { Mark, MARK, Notice, Spinner } from '../components/ui'
import { usePageTitle } from '../lib/usePageTitle'
import type { Analysis, ResumeDetail } from '../types'

/** A printable version of one review. Use the browser's print → save as PDF. */
export function Report() {
  const { analysisId = '' } = useParams()
  usePageTitle('Report')
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [resume, setResume] = useState<ResumeDetail | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const found = await api.getAnalysis(analysisId)
        if (cancelled) return
        setAnalysis(found)
        const detail = await api.getResume(found.resume_id)
        if (!cancelled) setResume(detail)
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Could not load the report.')
      }
    })()
    return () => {
      cancelled = true
    }
  }, [analysisId])

  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-5 py-10">
        <Notice tone="error">{error}</Notice>
      </div>
    )
  }
  if (!analysis) {
    return (
      <div className="flex min-h-screen items-center justify-center text-ink-muted">
        <Spinner />
      </div>
    )
  }

  const priorities = analysis.priorities ?? []
  const applicable = analysis.category_scores.filter((c) => c.applicable)

  return (
    <div className="min-h-screen">
      <div className="mx-auto flex max-w-3xl items-center justify-between px-5 py-5 print:hidden">
        <Link
          to={`/analyses/${analysis.id}`}
          className="eyebrow text-ink-muted transition-colors hover:text-ink-text"
        >
          Back to the review
        </Link>
        <button
          type="button"
          onClick={() => window.print()}
          className="rounded-[3px] bg-ink-text px-4 py-2 text-sm font-medium text-ink transition-colors hover:bg-white"
        >
          Print / save as PDF
        </button>
      </div>

      <div className="mx-auto max-w-3xl px-5 pb-16 print:max-w-none print:px-0 print:pb-0">
        <article className="sheet p-10 print:p-0">
          <header className="border-b border-paper-edge pb-6">
            <p className="eyebrow text-graphite-muted">Proof · Resume review report</p>
            <h1 className="mt-2 font-display text-3xl text-graphite">
              {analysis.resume_filename ?? 'Resume'}
            </h1>
            <p className="mt-2 font-mono text-xs text-graphite-muted">
              {new Date(analysis.created_at).toLocaleString()}
              {analysis.target_role ? ` · target role: ${analysis.target_role}` : ''} · engine v
              {analysis.engine_version}
            </p>
          </header>

          <section className="flex items-end gap-6 border-b border-paper-edge py-6">
            <div>
              <span className="font-display text-6xl leading-none text-graphite tabular-nums">
                {Math.round(analysis.overall_score)}
              </span>
              <span className="ml-1 font-mono text-sm text-graphite-muted">/100</span>
            </div>
            <p className="max-w-md pb-1 text-sm leading-relaxed text-graphite-muted">
              {analysis.verdict}
            </p>
          </section>

          <section className="border-b border-paper-edge py-6" style={{ breakInside: 'avoid' }}>
            <h2 className="eyebrow text-graphite-muted">Category scores</h2>
            <table className="mt-3 w-full text-sm">
              <tbody>
                {applicable.map((category) => (
                  <tr key={category.category} className="border-b border-paper-shade last:border-0">
                    <td className="py-1.5 pr-4 text-graphite">{category.label}</td>
                    <td className="py-1.5 pr-4 text-right font-mono text-graphite tabular-nums">
                      {Math.round(category.score)}/100
                    </td>
                    <td className="py-1.5 text-xs text-graphite-muted">
                      {category.critical_count > 0
                        ? `${category.critical_count} critical`
                        : category.finding_count > 0
                          ? `${category.finding_count} finding(s)`
                          : 'clear'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          {priorities.length > 0 && (
            <section className="border-b border-paper-edge py-6" style={{ breakInside: 'avoid' }}>
              <h2 className="eyebrow text-graphite-muted">Fix these first</h2>
              <ol className="mt-3 space-y-2.5">
                {priorities.map((finding, index) => (
                  <li key={finding.id} className="flex gap-3 text-sm">
                    <span className="font-mono text-xs text-graphite-muted">
                      {String(index + 1).padStart(2, '0')}
                    </span>
                    <span>
                      <span className="font-medium text-graphite">{finding.title}.</span>{' '}
                      <span className="text-graphite-muted">{finding.fix}</span>
                    </span>
                  </li>
                ))}
              </ol>
            </section>
          )}

          <section className="border-b border-paper-edge py-6">
            <h2 className="eyebrow text-graphite-muted">All findings by resume section</h2>
            {(() => {
              const grouped = new Map<string, typeof analysis.findings>()
              for (const finding of analysis.findings) {
                const key = finding.section ?? 'document'
                const bucket = grouped.get(key)
                if (bucket) bucket.push(finding)
                else grouped.set(key, [finding])
              }
              const order = [
                'document',
                ...(analysis.parsed_snapshot?.sections ?? [])
                  .map((section) => section.name)
                  .filter((name) => name !== 'unknown' && grouped.has(name)),
                ...[...grouped.keys()].filter((name) => name !== 'document'),
              ].filter((name, index, all) => grouped.has(name) && all.indexOf(name) === index)
              return order.map((key) => (
                <div key={key} style={{ breakInside: 'avoid' }}>
                  <h3 className="mt-5 mb-2 text-[12px] font-bold tracking-wide text-graphite-muted uppercase">
                    {sectionLabel(key)}
                  </h3>
                  <div className="space-y-4">
                    {grouped.get(key)!.map((finding) => (
                    <div key={finding.id} className="flex gap-3" style={{ breakInside: 'avoid' }}>
                      <Mark severity={finding.severity} size={18} />
                      <div className="min-w-0 text-sm">
                        <p className="font-medium text-graphite">
                          {finding.title}
                          <span className="ml-2 font-mono text-[10px] tracking-wider text-graphite-muted uppercase">
                            {finding.category_label}
                          </span>
                        </p>
                        <p className="mt-1 leading-relaxed text-graphite-muted">{finding.detail}</p>
                        {finding.evidence.length > 0 && (
                          <ul className="mt-1.5 space-y-1">
                            {finding.evidence.map((item, i) => (
                              <li
                                key={i}
                                className="border-l-2 pl-2 font-mono text-[11px] text-graphite-muted"
                                style={{ borderColor: MARK[finding.severity].color }}
                              >
                                {item}
                              </li>
                            ))}
                          </ul>
                        )}
                        {finding.fix && (
                          <p className="mt-1.5 leading-relaxed text-graphite">
                            <span className="eyebrow mr-2 text-graphite-muted">Fix</span>
                            {finding.fix}
                          </p>
                        )}
                      </div>
                    </div>
                    ))}
                  </div>
                </div>
              ))
            })()}
          </section>

          {analysis.keyword_report && (
            <section className="border-b border-paper-edge py-6" style={{ breakInside: 'avoid' }}>
              <h2 className="eyebrow text-graphite-muted">
                Job match: {Math.round(analysis.keyword_report.coverage * 100)}% of key terms
              </h2>
              {analysis.keyword_report.missing.length > 0 && (
                <p className="mt-2 text-sm leading-relaxed text-graphite-muted">
                  <span className="font-medium text-graphite">No evidence found for: </span>
                  {analysis.keyword_report.missing.map((t) => t.term).join(', ')}
                </p>
              )}
            </section>
          )}

          {analysis.ai_review && (
            <section className="border-b border-paper-edge py-6">
              <h2 className="eyebrow text-graphite-muted">AI review</h2>
              <p className="mt-2 text-sm leading-relaxed text-graphite">
                {analysis.ai_review.overall_impression}
              </p>
              {analysis.ai_review.bullet_rewrites.length > 0 && (
                <div className="mt-4 space-y-3">
                  {analysis.ai_review.bullet_rewrites.map((rewrite, i) => (
                    <div key={i} className="text-[12px]" style={{ breakInside: 'avoid' }}>
                      <p className="font-mono text-graphite-muted line-through">{rewrite.original}</p>
                      <p className="mt-1 border-l-2 border-[color:var(--color-mark-positive)] pl-2 font-mono text-graphite">
                        {rewrite.improved}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </section>
          )}

          <section className="py-6">
            <h2 className="eyebrow text-graphite-muted">Appendix: extracted text</h2>
            <pre className="mt-3 font-mono text-[10.5px] leading-relaxed whitespace-pre-wrap break-words text-graphite-muted">
              {resume?.raw_text ?? '…'}
            </pre>
          </section>
        </article>
      </div>
    </div>
  )
}
