import { useEffect, useRef, useState } from 'react'
import type { CSSProperties } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { useFeedback } from '../components/feedback'
import { FindingsList } from '../components/Findings'
import { AIPanel, KeywordPanel, SnapshotPanel } from '../components/Panels'
import { ProofSheet } from '../components/ProofSheet'
import { Button, Notice, Skeleton } from '../components/ui'
import { Scoreboard } from '../components/Verdict'
import { usePageTitle } from '../lib/usePageTitle'
import type { Analysis, CompareResult, Finding, ResumeDetail } from '../types'

export function Result() {
  const { analysisId = '' } = useParams()
  usePageTitle('Review')
  const navigate = useNavigate()
  const { health } = useAuth()
  const { toast } = useFeedback()

  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [resume, setResume] = useState<ResumeDetail | null>(null)
  const [compare, setCompare] = useState<CompareResult | null>(null)
  const [activeId, setActiveId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [aiRunning, setAiRunning] = useState(false)
  const [rerunning, setRerunning] = useState(false)

  const sourceRef = useRef<HTMLDivElement>(null)
  const findingsRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let cancelled = false
    setAnalysis(null)
    setResume(null)
    setCompare(null)
    setActiveId(null)
    ;(async () => {
      try {
        const found = await api.getAnalysis(analysisId)
        if (cancelled) return
        setAnalysis(found)

        api
          .compare(analysisId)
          .then((result) => !cancelled && setCompare(result))
          .catch(() => undefined) // 404 = nothing earlier to compare against
        const detail = await api.getResume(found.resume_id)
        if (!cancelled) setResume(detail)
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Could not load the review.')
      }
    })()
    return () => {
      cancelled = true
    }
  }, [analysisId])

  async function runAI() {
    setAiRunning(true)
    try {
      const updated = await api.runAIReview(analysisId)
      setAnalysis(updated)
      toast('success', 'AI review added.')
    } catch (err) {
      toast(
        'error',
        err instanceof ApiError ? err.message : 'The AI review could not be completed.',
      )
    } finally {
      setAiRunning(false)
    }
  }

  async function rerun() {
    if (!analysis) return
    setRerunning(true)
    try {
      const fresh = await api.analyze(analysis.resume_id, {
        target_role: analysis.target_role,
        job_description: analysis.job_description,
        include_ai: Boolean(analysis.ai_review) && (health?.ai_available ?? false),
      })
      toast('success', 'Review re-run with the current engine.')
      navigate(`/analyses/${fresh.id}`)
    } catch (err) {
      toast('error', err instanceof ApiError ? err.message : 'The review could not be re-run.')
    } finally {
      setRerunning(false)
    }
  }

  function showFinding(finding: Finding) {
    setActiveId(finding.id)
    const target = finding.evidence.length > 0 ? sourceRef : findingsRef
    target.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  if (error) return <Notice tone="error">{error}</Notice>
  if (!analysis) {
    return (
      <div className="space-y-8" aria-hidden="true">
        <div>
          <Skeleton className="h-4 w-32" />
          <Skeleton className="mt-4 h-8 w-48" />
        </div>
        <Skeleton className="h-40" />
        <Skeleton className="h-64" />
      </div>
    )
  }

  const priorities = analysis.priorities ?? []
  const projected = analysis.parsed_snapshot?.projected_score
  const showProjection =
    typeof projected === 'number' && projected > analysis.overall_score + 0.5
  const canRunAI =
    !analysis.ai_review && analysis.status === 'complete' && (health?.ai_available ?? false)
  const findingIds = new Set(analysis.findings.map((f) => f.id))
  const layoutIsRootCause =
    findingIds.has('ats.multi_column') &&
    [...findingIds].some((id) => id.startsWith('structure.empty_'))
  const showJobMatchCta = !analysis.keyword_report && !analysis.job_description

  return (
    <div>
      {/* Header */}
      <Link
        to={`/resumes/${analysis.resume_id}`}
        className="text-[13px] text-ink-muted transition-colors hover:text-ink-text"
      >
        Back to <span className="font-medium text-brand">{analysis.resume_filename ?? 'Resume'}</span>
      </Link>
      <div className="mt-3 flex flex-wrap items-end gap-x-8 gap-y-4">
        <div className="flex-1">
          <h1 className="text-[26px] leading-tight">Review</h1>
          <p className="mt-1.5 text-[13.5px] text-ink-muted">
            {new Date(analysis.created_at).toLocaleDateString(undefined, {
              dateStyle: 'medium',
            })}
            {analysis.target_role ? ` · for ${analysis.target_role}` : ''}
          </p>
        </div>
        <div className="flex items-center gap-5">
          <Link
            to={`/analyses/${analysis.id}/report`}
            className="text-sm font-medium text-brand hover:underline"
          >
            Print report
          </Link>
          <Button onClick={() => void rerun()} loading={rerunning}>
            {rerunning ? 'Re-running…' : 'Re-run review'}
          </Button>
        </div>
      </div>

      {/* Scoreboard: the focal point */}
      <Scoreboard
        score={analysis.overall_score}
        band={analysis.band}
        verdict={analysis.verdict}
        categories={analysis.category_scores}
        compare={compare}
      />

      {/* Fix these first */}
      {priorities.length > 0 && (
        <section className="mt-11" aria-label="Priority fixes">
          <div className="flex flex-wrap items-baseline gap-4">
            <h2 className="section-title">Fix these first</h2>
            {showProjection && (
              <span className="ml-auto text-[13.5px] text-ink-muted">
                Fixing {priorities.length === 1 ? 'this' : `all ${priorities.length}`} takes it to about{' '}
                <span className="font-mono font-semibold text-brand">
                  {projected.toFixed(0)}/100
                </span>
              </span>
            )}
          </div>

          {layoutIsRootCause && (
            <p className="mt-3 max-w-[640px] text-[13.5px] leading-relaxed text-ink-muted">
              <span className="font-semibold text-ink-text">One layout problem is behind
              several of these.</span>{' '}
              The multi-column page scatters content between the columns, which empties sections
              and hides bullets from the parser. Fix the layout first, then re-run. The
              downstream findings clear together.
            </p>
          )}

          <ol className="mt-1.5">
            {priorities.map((finding, index) => (
              <li
                key={finding.id}
                className="rise flex flex-wrap items-baseline gap-x-5 gap-y-1.5 border-b border-ink-line py-4 last:border-0"
                style={{ '--i': Math.min(index, 8) } as CSSProperties}
              >
                <span className="w-5 shrink-0 text-[19px] font-bold text-[#cfccc0]">
                  {index + 1}
                </span>
                <span className="min-w-0 flex-1 basis-72 text-[15px] leading-relaxed">
                  <span className="font-semibold">{finding.title}.</span>{' '}
                  <span className="text-[14.5px] text-ink-muted">{finding.fix}</span>
                </span>
                <span className="flex shrink-0 items-baseline gap-5">
                  {finding.overall_gain !== undefined && finding.overall_gain > 0 && (
                    <span className="font-mono text-[13px] text-ink-muted tabular-nums">
                      +{finding.overall_gain.toFixed(1)}
                    </span>
                  )}
                  <button
                    type="button"
                    onClick={() => showFinding(finding)}
                    className="text-sm font-medium text-brand hover:underline"
                  >
                    Show in resume
                  </button>
                </span>
              </li>
            ))}
          </ol>
        </section>
      )}

      {/* Source */}
      <section className="mt-11 scroll-mt-6" ref={sourceRef} aria-label="Source">
        {resume ? (
          <ProofSheet
            text={resume.raw_text}
            findings={analysis.findings}
            activeFindingId={activeId}
            onSelectFinding={setActiveId}
          />
        ) : (
          <Skeleton className="h-[16rem]" />
        )}
      </section>

      {/* Findings */}
      <section className="mt-11 scroll-mt-6" ref={findingsRef} aria-label="Findings">
        <FindingsList
          findings={analysis.findings}
          activeId={activeId}
          onSelect={setActiveId}
          sectionOrder={(analysis.parsed_snapshot?.sections ?? [])
            .map((section) => section.name)
            .filter((name) => name !== 'unknown')}
        />
      </section>

      {/* Parsed record */}
      <SnapshotPanel snapshot={analysis.parsed_snapshot} />

      {/* Job match */}
      {analysis.keyword_report ? (
        <KeywordPanel report={analysis.keyword_report} />
      ) : showJobMatchCta ? (
        <section className="mt-9 border-t border-ink-line pt-6" aria-label="Job match">
          <div className="flex flex-wrap items-baseline gap-x-6 gap-y-2">
            <h2 className="section-title">Job match</h2>
            <p className="max-w-[560px] flex-1 basis-72 text-sm leading-relaxed text-ink-muted">
              This review ran without a job posting. Paste one and Proof scores how well the
              resume covers its weighted requirements.
            </p>
            <Link
              to={`/resumes/${analysis.resume_id}`}
              className="shrink-0 text-sm font-medium text-brand hover:underline"
            >
              Run with a job posting
            </Link>
          </div>
        </section>
      ) : null}

      {/* AI review */}
      <section className="mt-9 border-t border-ink-line pt-6" aria-label="AI review section">
        <AIPanel
          review={analysis.ai_review}
          error={analysis.ai_error}
          model={analysis.ai_model}
          action={
            canRunAI ? (
              <Button onClick={() => void runAI()} loading={aiRunning}>
                {aiRunning ? 'Reviewing…' : 'Run the AI review'}
              </Button>
            ) : undefined
          }
        />
      </section>
    </div>
  )
}
