import { useCallback, useEffect, useMemo, useState, type CSSProperties } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { useFeedback } from '../components/feedback'
import { Button, Empty, Notice, Skeleton } from '../components/ui'
import { usePageTitle } from '../lib/usePageTitle'
import type { AnalysisSummary } from '../types'

export function History() {
  usePageTitle('History')
  const { toast, confirm } = useFeedback()
  const [items, setItems] = useState<AnalysisSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [sort, setSort] = useState<'newest' | 'highest' | 'lowest'>('newest')
  const sorted = useMemo(() => {
    if (items === null) return null
    const copy = [...items]
    if (sort === 'highest') copy.sort((a, b) => b.overall_score - a.overall_score)
    if (sort === 'lowest') copy.sort((a, b) => a.overall_score - b.overall_score)
    return copy
  }, [items, sort])

  const refresh = useCallback(async () => {
    try {
      setItems(await api.listAnalyses({ limit: 50 }))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load your history.')
      setItems([])
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  async function remove(item: AnalysisSummary) {
    const confirmed = await confirm({
      title: 'Delete this review?',
      body: `The ${Math.round(item.overall_score)}-point review of ${
        item.resume_filename ?? 'this resume'
      } is removed from your history. The resume itself is kept.`,
      confirmLabel: 'Delete',
      danger: true,
    })
    if (!confirmed) return
    try {
      await api.deleteAnalysis(item.id)
      toast('success', 'Review deleted.')
      await refresh()
    } catch (err) {
      toast('error', err instanceof Error ? err.message : 'Could not delete that review.')
    }
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-baseline gap-x-6 gap-y-1 border-b border-ink-line">
        <h1 className="pb-3 text-[26px] leading-tight">History</h1>
        <div className="ml-auto flex gap-5 pb-3 text-[13.5px]">
          {(['newest', 'highest', 'lowest'] as const).map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => setSort(option)}
              aria-pressed={sort === option}
              className={sort === option ? 'font-semibold text-ink-text' : 'text-ink-muted hover:text-ink-text'}
            >
              {option === 'newest' ? 'Newest' : option === 'highest' ? 'Highest' : 'Lowest'}
            </button>
          ))}
        </div>
      </div>
      <p className="mt-1.5 text-sm text-ink-muted">
        Every review you've run. Re-run after each revision to see the score move.
      </p>

      {error && <Notice tone="error">{error}</Notice>}

      {items === null ? (
        <div className="space-y-2" aria-hidden="true">
          <Skeleton className="h-[70px]" />
          <Skeleton className="h-[70px]" />
          <Skeleton className="h-[70px]" />
        </div>
      ) : items.length === 0 ? (
        <Empty
          title="No reviews yet"
          action={
            <Link to="/">
              <Button>Upload a resume</Button>
            </Link>
          }
        >
          Run your first review and it will show up here alongside its score.
        </Empty>
      ) : (
        <ul className="border-t border-ink-line">
          {sorted!.map((item, index) => (
            <li
              key={item.id}
              className="group rise flex flex-wrap items-baseline gap-x-5 gap-y-1 border-b border-ink-faint py-3.5"
              style={{ '--i': Math.min(index, 8) } as CSSProperties}
            >
              <Link to={`/analyses/${item.id}`} className="min-w-0 flex-1 basis-64">
                <span className="text-[14.5px] font-semibold text-ink-text">
                  {item.resume_filename ?? 'Resume'}
                </span>
                <span className="ml-3 text-[13px] text-ink-dim">
                  {new Date(item.created_at).toLocaleString()}
                  {item.target_role ? ` · ${item.target_role}` : ''}
                  {item.has_ai_review ? ' · AI review' : ''}
                </span>
              </Link>
              <span className="font-mono text-[14.5px] font-semibold tabular-nums text-ink-text">
                {item.overall_score.toFixed(1)}
              </span>
              <span className="row-actions flex items-baseline gap-4">
                <Link to={`/analyses/${item.id}`} className="text-sm font-medium text-brand hover:underline">
                  View
                </Link>
                <button
                  type="button"
                  onClick={() => void remove(item)}
                  className="text-sm text-[color:var(--color-mark-critical)] hover:underline"
                >
                  Delete
                </button>
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
