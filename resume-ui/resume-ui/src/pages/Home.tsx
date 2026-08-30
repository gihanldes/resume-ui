import { useCallback, useEffect, useRef, useState, type CSSProperties, type DragEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { useFeedback } from '../components/feedback'
import { TrendChart, type TrendPoint } from '../components/TrendChart'
import { bandColor } from '../components/Verdict'
import { Button, Notice, Skeleton } from '../components/ui'
import { EmptyResumeArt, ScanIllustration } from '../components/art'
import { useCountUp } from '../lib/useCountUp'
import { usePageTitle } from '../lib/usePageTitle'
import type { Analysis, Resume, Stats } from '../types'

const ACCEPT = '.pdf,.docx,.txt,.md'

interface HomeData {
  resumes: Resume[]
  stats: Stats
  latest: Analysis | null
  trend: TrendPoint[]
}

function LatestBand({ latest, delta }: { latest: Analysis; delta: number | null }) {
  const shown = useCountUp(latest.overall_score)
  return (
    <section
      className="border-t border-ink-text border-b border-b-ink-line pt-6 pb-6"
      aria-label="Latest review"
    >
      <div className="flex flex-wrap items-end gap-x-10 gap-y-4">
        <div className="rise flex items-baseline gap-2">
          <span
            className="text-[52px] leading-[0.9] font-extrabold tracking-[-0.03em] tabular-nums"
            style={{ color: bandColor(latest.overall_score) }}
            aria-label={`${latest.overall_score.toFixed(1)} out of 100`}
          >
            {shown.toFixed(1)}
          </span>
          <span className="font-mono text-sm text-ink-dim">/100</span>
        </div>
        <div className="rise min-w-0 flex-1 basis-64" style={{ '--i': 1 } as CSSProperties}>
          <p className="text-[15px] font-bold">{latest.resume_filename ?? 'Latest resume'}</p>
          <p className="mt-0.5 text-[13.5px] text-ink-muted">
            Reviewed {new Date(latest.created_at).toLocaleDateString(undefined, { dateStyle: 'medium' })}
            {delta != null && delta !== 0 && (
              <span
                className="ml-2 font-mono font-semibold tabular-nums"
                style={{
                  color: delta > 0 ? 'var(--color-mark-positive)' : 'var(--color-mark-critical)',
                }}
              >
                {delta > 0 ? `+${delta.toFixed(1)}` : delta.toFixed(1)}
              </span>
            )}
          </p>
        </div>
        <div className="rise flex items-center gap-5" style={{ '--i': 2 } as CSSProperties}>
          <Link to={`/analyses/${latest.id}`}>
            <Button>Continue fixing</Button>
          </Link>
          <Link
            to={`/resumes/${latest.resume_id}`}
            className="text-sm font-medium text-brand hover:underline"
          >
            Run new review
          </Link>
        </div>
      </div>
    </section>
  )
}

export function Home() {
  usePageTitle('Home')
  const { user } = useAuth()
  const { toast, confirm } = useFeedback()
  const navigate = useNavigate()
  const inputRef = useRef<HTMLInputElement>(null)
  const [data, setData] = useState<HomeData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [dragging, setDragging] = useState(false)

  const load = useCallback(async () => {
    try {
      const [resumes, stats, history] = await Promise.all([
        api.listResumes(),
        api.stats(),
        api.listAnalyses({ limit: 50 }),
      ])
      const complete = history.filter((item) => item.status === 'complete')
      const latest = complete[0] ? await api.getAnalysis(complete[0].id) : null
      setData({
        resumes,
        stats,
        latest,
        trend: complete
          .slice()
          .reverse()
          .map((item) => ({
            id: item.id,
            score: item.overall_score,
            date: item.created_at,
            label: item.resume_filename ?? 'Resume',
          })),
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load your home page.')
      setData({ resumes: [], stats: { analysis_count: 0 } as Stats, latest: null, trend: [] })
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const upload = useCallback(
    async (file: File) => {
      setUploading(true)
      setError(null)
      try {
        const resume = await api.uploadResume(file)
        toast('success', `Uploaded ${resume.filename}.`)
        navigate(`/resumes/${resume.id}`, { state: { fresh: true } })
      } catch (err) {
        setError(err instanceof ApiError ? err.message : 'Upload failed. Check the file and try again.')
        setUploading(false)
      }
    },
    [navigate, toast],
  )

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setDragging(false)
    const file = event.dataTransfer.files?.[0]
    if (file) void upload(file)
  }

  async function remove(resume: Resume) {
    const confirmed = await confirm({
      title: `Delete "${resume.filename}"?`,
      body: `Its ${resume.analysis_count} review(s) are deleted with it. This can't be undone.`,
      confirmLabel: 'Delete',
      danger: true,
    })
    if (!confirmed) return
    try {
      await api.deleteResume(resume.id)
      toast('success', `Deleted ${resume.filename}.`)
      await load()
    } catch (err) {
      toast('error', err instanceof Error ? err.message : 'Could not delete that resume.')
    }
  }

  if (data === null) {
    return (
      <div className="space-y-6" aria-hidden="true">
        <Skeleton className="h-28" />
        <Skeleton className="h-40" />
        <Skeleton className="h-24" />
      </div>
    )
  }

  const { resumes, stats, latest, trend } = data
  const firstName = user?.full_name?.trim().split(/\s+/)[0]

  /* ------------------------------------------------ first run */
  if (resumes.length === 0) {
    return (
      <div
        onDragOver={(event) => {
          event.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        className="mx-auto max-w-xl py-10 text-center"
      >
        {error && <div className="mb-6 text-left"><Notice tone="error">{error}</Notice></div>}
        <div className="rise"><EmptyResumeArt /></div>
        <h1 className="rise mt-6 text-[26px] leading-tight" style={{ '--i': 1 } as CSSProperties}>
          {firstName ? `Welcome, ${firstName}.` : 'Welcome.'}
        </h1>
        <p className="rise mx-auto mt-2 max-w-md text-sm leading-relaxed text-ink-muted" style={{ '--i': 2 } as CSSProperties}>
          Upload a resume and Proof shows you the exact text a screening system reads, scores it
          across six categories, and prices every fix.
        </p>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT}
          className="sr-only"
          onChange={(event) => {
            const file = event.target.files?.[0]
            if (file) void upload(file)
            event.target.value = ''
          }}
        />
        <div className="rise mt-7" style={{ '--i': 3 } as CSSProperties}>
          {uploading ? (
            <div className="flex items-center justify-center gap-4 text-ink-text">
              <ScanIllustration width={44} />
              <span className="text-sm">Reading the file…</span>
            </div>
          ) : (
            <Button onClick={() => inputRef.current?.click()}>Upload a resume</Button>
          )}
          <p className="mt-3 text-[12.5px] text-ink-dim">
            {dragging ? 'Drop it anywhere on this page.' : 'PDF, DOCX or TXT up to 5 MB. Or drop it anywhere on this page.'}
          </p>
        </div>
        <ol className="rise mx-auto mt-12 flex max-w-lg flex-wrap justify-center gap-x-10 gap-y-4 border-t border-ink-line pt-6 text-left text-[13.5px] text-ink-muted" style={{ '--i': 4 } as CSSProperties}>
          <li><span className="font-mono font-semibold text-ink-text">1</span> Upload your resume</li>
          <li><span className="font-mono font-semibold text-ink-text">2</span> See what the screen sees</li>
          <li><span className="font-mono font-semibold text-ink-text">3</span> Fix in point order</li>
        </ol>
      </div>
    )
  }

  /* ------------------------------------------------ populated */
  const priorities = (latest?.priorities ?? []).slice(0, 3)
  return (
    <div
      onDragOver={(event) => {
        event.preventDefault()
        setDragging(true)
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
    >
      <h1 className="text-[26px] leading-tight">{firstName ? `Hello, ${firstName}` : 'Home'}</h1>
      <p className="mt-1.5 text-sm text-ink-muted">
        {stats.analysis_count} review{stats.analysis_count === 1 ? '' : 's'} across{' '}
        {resumes.length} resume{resumes.length === 1 ? '' : 's'}.
        {dragging ? ' Drop the file to upload it.' : ''}
      </p>

      {error && <div className="mt-4"><Notice tone="error">{error}</Notice></div>}

      {latest && (
        <div className="mt-5">
          <LatestBand latest={latest} delta={stats.delta ?? null} />
        </div>
      )}

      {priorities.length > 0 && latest && (
        <section className="mt-9" aria-label="Fix these next">
          <h2 className="section-title">Fix these next</h2>
          <ol className="mt-1.5">
            {priorities.map((finding, index) => (
              <li
                key={finding.id}
                className="rise flex flex-wrap items-baseline gap-x-5 gap-y-1 border-b border-ink-faint py-3.5 last:border-0"
                style={{ '--i': index } as CSSProperties}
              >
                <span className="w-5 shrink-0 text-[17px] font-bold text-[#cfccc0]">{index + 1}</span>
                <span className="min-w-0 flex-1 basis-72 text-sm leading-relaxed">
                  <span className="font-semibold">{finding.title}.</span>{' '}
                  <span className="text-ink-muted">{finding.fix}</span>
                </span>
                <span className="flex shrink-0 items-baseline gap-5">
                  {finding.overall_gain !== undefined && finding.overall_gain > 0 && (
                    <span className="font-mono text-[13px] text-ink-muted tabular-nums">
                      +{finding.overall_gain.toFixed(1)}
                    </span>
                  )}
                  <Link
                    to={`/analyses/${latest.id}`}
                    className="text-sm font-medium text-brand hover:underline"
                  >
                    Open
                  </Link>
                </span>
              </li>
            ))}
          </ol>
        </section>
      )}

      {trend.length >= 2 && (
        <section className="mt-9 border-t border-ink-line pt-6" aria-label="Score over time">
          <div className="flex flex-wrap items-baseline gap-x-4">
            <h2 className="section-title">Score over time</h2>
            <span className="text-[13px] text-ink-muted">click a point to open its review</span>
          </div>
          <div className="mt-2">
            <TrendChart points={trend} />
          </div>
        </section>
      )}

      <section className="mt-9 border-t border-ink-line pt-6" aria-label="Your resumes">
        <div className="flex flex-wrap items-baseline gap-x-6 gap-y-2">
          <h2 className="section-title">Your resumes</h2>
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPT}
            className="sr-only"
            onChange={(event) => {
              const file = event.target.files?.[0]
              if (file) void upload(file)
              event.target.value = ''
            }}
          />
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            disabled={uploading}
            className="ml-auto text-sm font-medium text-brand hover:underline disabled:cursor-not-allowed disabled:opacity-50"
          >
            {uploading ? 'Uploading…' : 'Upload a resume'}
          </button>
        </div>
        <ul className="mt-2">
          {resumes.map((resume, index) => (
            <li
              key={resume.id}
              className="group rise flex flex-wrap items-baseline gap-x-5 gap-y-1 border-b border-ink-faint py-3 last:border-0"
              style={{ '--i': Math.min(index, 8) } as CSSProperties}
            >
              <Link to={`/resumes/${resume.id}`} className="min-w-0 flex-1 basis-64">
                <span className="text-[14.5px] font-semibold text-ink-text">{resume.filename}</span>
                <span className="ml-3 text-[13px] text-ink-dim">
                  {resume.analysis_count} review{resume.analysis_count === 1 ? '' : 's'}
                </span>
              </Link>
              {resume.latest_score != null && (
                <span
                  className="font-mono text-[14px] font-semibold tabular-nums"
                  style={{ color: bandColor(resume.latest_score) }}
                >
                  {resume.latest_score.toFixed(1)}
                </span>
              )}
              <span className="row-actions flex items-baseline gap-4">
                <Link
                  to={`/resumes/${resume.id}`}
                  className="text-sm font-medium text-brand hover:underline"
                >
                  Review
                </Link>
                <button
                  type="button"
                  onClick={() => void remove(resume)}
                  className="text-sm text-[color:var(--color-mark-critical)] hover:underline"
                >
                  Delete
                </button>
              </span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
