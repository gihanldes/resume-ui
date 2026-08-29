import { useCallback, useEffect, useRef, useState, type CSSProperties, type FormEvent } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { useFeedback } from '../components/feedback'
import { Button, Field, Input, Notice, Skeleton, Textarea } from '../components/ui'
import { ScanIllustration } from '../components/art'
import { bandColor } from '../components/Verdict'
import { usePageTitle } from '../lib/usePageTitle'
import type { AnalysisSummary, ResumeDetail as ResumeDetailType } from '../types'

export function ResumeDetail() {
  const { resumeId = '' } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const { user, health } = useAuth()
  const { toast, confirm } = useFeedback()

  const [resume, setResume] = useState<ResumeDetailType | null>(null)
  const [reviews, setReviews] = useState<AnalysisSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  usePageTitle(resume?.filename ?? 'Resume')

  const fresh = Boolean((location.state as { fresh?: boolean } | null)?.fresh)
  const [panelOpen, setPanelOpen] = useState(fresh)
  const [targetRole, setTargetRole] = useState('')
  const [jobDescription, setJobDescription] = useState('')
  const [includeAI, setIncludeAI] = useState(true)
  const [running, setRunning] = useState(false)

  const [renaming, setRenaming] = useState(false)
  const [draftName, setDraftName] = useState('')
  const [textOpen, setTextOpen] = useState(false)
  const renameInFlight = useRef(false)

  const aiAvailable = health?.ai_available ?? false

  const load = useCallback(async () => {
    try {
      const [detail, history] = await Promise.all([
        api.getResume(resumeId),
        api.listAnalyses({ resume_id: resumeId, limit: 50 }),
      ])
      setResume(detail)
      setReviews(history)
      if (history.length === 0) setPanelOpen(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load that resume.')
    }
  }, [resumeId])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    if (user?.target_role) setTargetRole(user.target_role)
  }, [user])

  useEffect(() => {
    if (fresh) navigate(location.pathname, { replace: true, state: {} })
  }, [fresh, navigate, location.pathname])

  async function run() {
    setRunning(true)
    setError(null)
    try {
      const analysis = await api.analyze(resumeId, {
        target_role: targetRole || null,
        job_description: jobDescription || null,
        include_ai: includeAI && aiAvailable,
      })
      navigate(`/analyses/${analysis.id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'The review could not be run.')
      setRunning(false)
    }
  }

  async function saveName(event: FormEvent) {
    event.preventDefault()
    if (renameInFlight.current) return
    const name = draftName.trim()
    if (!name || !resume || name === resume.filename) {
      setRenaming(false)
      return
    }
    renameInFlight.current = true
    try {
      const updated = await api.renameResume(resume.id, name)
      setResume({ ...resume, filename: updated.filename })
      toast('success', 'Resume renamed.')
    } catch (err) {
      toast('error', err instanceof Error ? err.message : 'Could not rename it.')
    } finally {
      renameInFlight.current = false
      setRenaming(false)
    }
  }

  async function remove() {
    if (!resume) return
    const confirmed = await confirm({
      title: `Delete "${resume.filename}"?`,
      body: `Its ${reviews?.length ?? 0} review(s) are deleted with it. This can't be undone.`,
      confirmLabel: 'Delete',
      danger: true,
    })
    if (!confirmed) return
    try {
      await api.deleteResume(resume.id)
      toast('success', `Deleted ${resume.filename}.`)
      navigate('/resumes')
    } catch (err) {
      toast('error', err instanceof Error ? err.message : 'Could not delete that resume.')
    }
  }

  if (error && !resume) return <Notice tone="error">{error}</Notice>
  if (!resume || reviews === null) {
    return (
      <div className="space-y-6" aria-hidden="true">
        <Skeleton className="h-24" />
        <Skeleton className="h-12" />
        <Skeleton className="h-12" />
      </div>
    )
  }

  return (
    <div>
      <Link to="/resumes" className="text-[13px] text-ink-muted transition-colors hover:text-ink-text">
        Back to resumes
      </Link>

      {/* Header */}
      <div className="mt-3 flex flex-wrap items-end gap-x-8 gap-y-4">
        <div className="min-w-0 flex-1 basis-72">
          {renaming ? (
            <form onSubmit={saveName} className="max-w-md">
              <Input
                value={draftName}
                onChange={(event) => setDraftName(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Escape') setRenaming(false)
                }}
                onBlur={saveName}
                maxLength={255}
                autoFocus
                aria-label="Resume name"
              />
            </form>
          ) : (
            <h1 className="truncate text-[26px] leading-tight">{resume.filename}</h1>
          )}
          <p className="mt-1.5 font-mono text-xs text-ink-muted">
            {resume.word_count} words · {resume.page_count} page(s) · uploaded{' '}
            {new Date(resume.created_at).toLocaleDateString()}
          </p>
        </div>
        <div className="flex items-center gap-5">
          <button
            type="button"
            onClick={() => {
              setDraftName(resume.filename)
              setRenaming(true)
            }}
            className="text-sm font-medium text-brand hover:underline"
          >
            Rename
          </button>
          <button
            type="button"
            onClick={() => void remove()}
            className="text-sm text-[color:var(--color-mark-critical)] hover:underline"
          >
            Delete
          </button>
          {!panelOpen && !running && (
            <Button onClick={() => setPanelOpen(true)}>Run new review</Button>
          )}
        </div>
      </div>

      {error && <div className="mt-5"><Notice tone="error">{error}</Notice></div>}

      {/* Setup panel */}
      {(panelOpen || running) && (
        <section className="rise mt-8 border-t border-ink-text pt-6" aria-label="Set up the review">
          {running ? (
            <ReviewingState withAI={includeAI && aiAvailable} model={health?.ai_model ?? null} />
          ) : (
            <>
              {reviews.length === 0 && (
                <p className="mb-4 max-w-[560px] text-sm leading-relaxed text-ink-muted">
                  First review: it takes a few seconds, or about a minute with the AI critique on.
                </p>
              )}
              <div className="grid gap-6 lg:grid-cols-2">
                <Field label="Target role" hint="Shapes the AI review's judgement of seniority and fit.">
                  <Input
                    value={targetRole}
                    onChange={(event) => setTargetRole(event.target.value)}
                    placeholder="Senior Backend Engineer"
                  />
                </Field>
                <div />
                <Field
                  label="Job description"
                  hint="Optional. Paste one to score how well this resume matches it. The Job match category only runs with one."
                >
                  <Textarea
                    value={jobDescription}
                    onChange={(event) => setJobDescription(event.target.value)}
                    rows={8}
                    placeholder="Paste the full posting, including the requirements list."
                  />
                </Field>
                <div className="space-y-5 pt-1">
                  <label className="flex items-start gap-3">
                    <input
                      type="checkbox"
                      checked={includeAI && aiAvailable}
                      disabled={!aiAvailable}
                      onChange={(event) => setIncludeAI(event.target.checked)}
                      className="mt-0.5 size-4 accent-[#2a5d46]"
                    />
                    <span className="text-sm">
                      <span className="block text-ink-text">Include the AI review</span>
                      <span className="mt-0.5 block text-xs leading-relaxed text-ink-muted">
                        {aiAvailable
                          ? `Adds a written critique and rewritten bullets from ${health?.ai_model}. Adds up to a minute.`
                          : 'Unavailable: the server has no OPENAI_API_KEY set. The rule-based review still runs in full.'}
                      </span>
                    </span>
                  </label>
                  <div className="flex items-center gap-5">
                    <Button onClick={() => void run()}>Run the review</Button>
                    {reviews.length > 0 && (
                      <button
                        type="button"
                        onClick={() => setPanelOpen(false)}
                        className="text-sm text-ink-muted transition-colors hover:text-ink-text"
                      >
                        Cancel
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </>
          )}
        </section>
      )}

      {/* Reviews */}
      <section className="mt-9 border-t border-ink-line pt-6" aria-label="Reviews">
        <h2 className="section-title">Reviews</h2>
        {reviews.length === 0 ? (
          <p className="mt-2 text-sm text-ink-muted">
            No reviews yet. Run the first one above.
          </p>
        ) : (
          <ul className="mt-2">
            {reviews.map((item, index) => {
              const previous = reviews[index + 1]
              const delta =
                previous && item.status === 'complete' && previous.status === 'complete'
                  ? Math.round((item.overall_score - previous.overall_score) * 10) / 10
                  : null
              return (
                <li
                  key={item.id}
                  className="group rise flex flex-wrap items-baseline gap-x-5 gap-y-1 border-b border-ink-faint py-3 last:border-0"
                  style={{ '--i': Math.min(index, 8) } as CSSProperties}
                >
                  <span className="min-w-0 flex-1 basis-64 text-sm text-ink-muted">
                    {new Date(item.created_at).toLocaleString()}
                    {item.target_role ? ` · ${item.target_role}` : ''}
                    {item.has_ai_review ? ' · AI review' : ''}
                  </span>
                  {delta != null && delta !== 0 && (
                    <span
                      className="font-mono text-[12.5px] tabular-nums"
                      style={{
                        color:
                          delta > 0 ? 'var(--color-mark-positive)' : 'var(--color-mark-critical)',
                      }}
                    >
                      {delta > 0 ? `+${delta.toFixed(1)}` : delta.toFixed(1)}
                    </span>
                  )}
                  <span
                    className="font-mono text-[14.5px] font-semibold tabular-nums"
                    style={{ color: bandColor(item.overall_score) }}
                  >
                    {item.overall_score.toFixed(1)}
                  </span>
                  <Link
                    to={`/analyses/${item.id}`}
                    className="row-actions text-sm font-medium text-brand hover:underline"
                  >
                    View
                  </Link>
                </li>
              )
            })}
          </ul>
        )}
      </section>

      {/* Extracted text */}
      <section className="mt-9 border-t border-ink-line pt-6" aria-label="Extracted text">
        <div className="flex items-baseline gap-4">
          <h2 className="section-title">Extracted text</h2>
          <button
            type="button"
            onClick={() => setTextOpen((value) => !value)}
            aria-expanded={textOpen}
            className="text-sm font-medium text-brand hover:underline"
          >
            {textOpen ? 'Collapse' : 'Expand'}
          </button>
        </div>
        {textOpen && (
          <pre className="well mt-3 max-h-96 overflow-y-auto px-5 py-4 font-mono text-[11.5px] leading-relaxed whitespace-pre-wrap break-words text-ink-text">
            {resume.raw_text}
          </pre>
        )}
      </section>
    </div>
  )
}

function ReviewingState({ withAI, model }: { withAI: boolean; model: string | null }) {
  const [seconds, setSeconds] = useState(0)
  useEffect(() => {
    const timer = setInterval(() => setSeconds((value) => value + 1), 1000)
    return () => clearInterval(timer)
  }, [])
  const clock = `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
  return (
    <div className="rise flex flex-wrap items-center gap-8 py-4">
      <ScanIllustration width={88} />
      <div className="min-w-0 flex-1 basis-60">
        <h2 className="text-lg font-bold tracking-tight">Reviewing this resume</h2>
        <p className="mt-1.5 max-w-[440px] text-sm leading-relaxed text-ink-muted">
          Parsing the layout, then scoring all six categories against the rule book.
          {withAI
            ? ` After that ${model ?? 'the AI reviewer'} writes the critique, which can take up to a minute.`
            : ''}
        </p>
        <p className="mt-3 font-mono text-[13px] text-ink-dim tabular-nums">{clock} elapsed</p>
      </div>
    </div>
  )
}
