import { useCallback, useEffect, useRef, useState, type CSSProperties, type DragEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, ApiError } from '../api/client'
import { useFeedback } from '../components/feedback'
import { bandColor } from '../components/Verdict'
import { Button, Empty, Notice, Skeleton } from '../components/ui'
import { EmptyResumeArt, ScanIllustration } from '../components/art'
import { usePageTitle } from '../lib/usePageTitle'
import type { Resume } from '../types'

const ACCEPT = '.pdf,.docx,.txt,.md'

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

export function Resumes() {
  const { toast, confirm } = useFeedback()
  const navigate = useNavigate()
  const inputRef = useRef<HTMLInputElement>(null)
  usePageTitle('Your resumes')

  const [resumes, setResumes] = useState<Resume[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [dragging, setDragging] = useState(false)

  const refresh = useCallback(async () => {
    try {
      setResumes(await api.listResumes())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load your resumes.')
      setResumes([])
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const upload = useCallback(
    async (file: File) => {
      setUploading(true)
      setError(null)
      try {
        const resume = await api.uploadResume(file)
        toast('success', `Uploaded ${resume.filename}.`)
        navigate(`/resumes/${resume.id}`, { state: { fresh: true } })
      } catch (err) {
        setError(
          err instanceof ApiError ? err.message : 'Upload failed. Check the file and try again.',
        )
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
      await refresh()
    } catch (err) {
      toast('error', err instanceof Error ? err.message : 'Could not delete that resume.')
    }
  }

  return (
    <div>
      <h1 className="text-[26px] leading-tight">Your resumes</h1>
      <p className="mt-1.5 text-sm text-ink-muted">
        Every version you upload stays here, so you can re-run reviews after each revision.
      </p>

      {error && <div className="mt-4"><Notice tone="error">{error}</Notice></div>}

      <div
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        className={`mt-9 flex flex-wrap items-center gap-6 rounded-md border-[1.5px] border-dashed px-7 py-7 transition-colors ${
          dragging ? 'border-brand bg-tint-positive' : 'border-[#cfccc0]'
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT}
          className="sr-only"
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (file) void upload(file)
            e.target.value = ''
          }}
        />
        {uploading ? (
          <div className="flex items-center gap-5 text-ink-text">
            <ScanIllustration width={46} />
            <span className="text-sm">Reading the file…</span>
          </div>
        ) : (
          <>
            <div className="min-w-0 flex-1 basis-72">
              <h2 className="text-base font-bold">Drop a resume to screen it</h2>
              <p className="mt-1 text-[13.5px] leading-relaxed text-ink-muted">
                PDF, DOCX or TXT up to 5 MB. Read as plain text, exactly what a screening
                system sees.
              </p>
            </div>
            <Button onClick={() => inputRef.current?.click()}>Choose a file</Button>
          </>
        )}
      </div>

      {resumes === null ? (
        <div className="mt-9 space-y-3" aria-hidden="true">
          <Skeleton className="h-12" />
          <Skeleton className="h-12" />
        </div>
      ) : resumes.length === 0 ? (
        <div className="mt-9">
          <Empty title="Nothing uploaded yet" art={<EmptyResumeArt />}>
            Once you upload a resume it stays in your account, so you can re-run a review after
            each revision and watch the score move.
          </Empty>
        </div>
      ) : (
        <section className="mt-10" aria-label="Uploaded resumes">
          <h2 className="section-title border-b border-ink-line pb-3">Your resumes</h2>
          <ul>
            {resumes.map((resume, index) => (
              <li
                key={resume.id}
                className="group rise flex flex-wrap items-baseline gap-x-5 gap-y-1 border-b border-ink-faint py-3.5"
                style={{ '--i': Math.min(index, 8) } as CSSProperties}
              >
                <Link to={`/resumes/${resume.id}`} className="min-w-0 flex-1 basis-64">
                  <span className="text-[14.5px] font-semibold text-ink-text">
                    {resume.filename}
                  </span>
                  <span className="ml-3 text-[13px] text-ink-dim">
                    {formatDate(resume.created_at)} · {resume.word_count} words ·{' '}
                    {resume.page_count} page(s) · {resume.analysis_count} review
                    {resume.analysis_count === 1 ? '' : 's'}
                  </span>
                </Link>

                {resume.latest_score != null && (
                  <span
                    className="font-mono text-[14.5px] font-semibold tabular-nums"
                    style={{ color: bandColor(resume.latest_score) }}
                  >
                    {resume.latest_score.toFixed(1)}
                  </span>
                )}

                <span className="row-actions flex items-baseline gap-4">
                  <button
                    type="button"
                    onClick={() => navigate(`/resumes/${resume.id}`)}
                    className="text-sm font-medium text-brand hover:underline"
                  >
                    Review
                  </button>
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
      )}
    </div>
  )
}
