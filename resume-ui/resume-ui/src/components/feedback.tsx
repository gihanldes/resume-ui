import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react'
import { Button } from './ui'

/** App-wide toasts and a promise-based confirm dialog, replacing window.confirm. */

interface ToastItem {
  id: number
  kind: 'success' | 'error' | 'info'
  text: string
}

interface ConfirmOptions {
  title: string
  body: string
  confirmLabel?: string
  danger?: boolean
}

interface FeedbackValue {
  toast: (kind: ToastItem['kind'], text: string) => void
  confirm: (options: ConfirmOptions) => Promise<boolean>
}

const FeedbackContext = createContext<FeedbackValue | null>(null)
let nextToastId = 1

const TOAST_TONES: Record<ToastItem['kind'], string> = {
  success: 'text-[color:var(--color-mark-positive)]',
  error: 'text-[color:var(--color-mark-critical)]',
  info: 'text-ink-text',
}

export function FeedbackProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([])
  const [pending, setPending] = useState<{
    options: ConfirmOptions
    resolve: (value: boolean) => void
  } | null>(null)

  const toast = useCallback((kind: ToastItem['kind'], text: string) => {
    const id = nextToastId++
    setToasts((current) => [...current, { id, kind, text }])
    setTimeout(() => setToasts((current) => current.filter((t) => t.id !== id)), 4500)
  }, [])

  const confirm = useCallback(
    (options: ConfirmOptions) =>
      new Promise<boolean>((resolve) => setPending({ options, resolve })),
    [],
  )

  const settle = useCallback(
    (value: boolean) => {
      pending?.resolve(value)
      setPending(null)
    },
    [pending],
  )

  useEffect(() => {
    if (!pending) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') settle(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [pending, settle])

  return (
    <FeedbackContext.Provider value={{ toast, confirm }}>
      {children}

      {pending && (
        <div
          className="fixed inset-0 z-50 grid place-items-center bg-[#1c1b16]/40 p-5"
          onClick={() => settle(false)}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="confirm-title"
            className="w-full max-w-sm rounded-lg border border-ink-line bg-ink p-6 shadow-[0_16px_40px_-12px_rgba(28,27,22,0.28)]"
            onClick={(event) => event.stopPropagation()}
          >
            <h2 id="confirm-title" className="font-display text-xl text-ink-text">
              {pending.options.title}
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-ink-muted">{pending.options.body}</p>
            <div className="mt-6 flex justify-end gap-2">
              <Button variant="ghost" autoFocus onClick={() => settle(false)}>
                Cancel
              </Button>
              <Button
                variant={pending.options.danger ? 'danger' : 'primary'}
                onClick={() => settle(true)}
              >
                {pending.options.confirmLabel ?? 'Confirm'}
              </Button>
            </div>
          </div>
        </div>
      )}

      <div className="pointer-events-none fixed right-4 bottom-4 z-50 flex w-72 max-w-[calc(100vw-2rem)] flex-col gap-2">
        {toasts.map((item) => (
          <div
            key={item.id}
            role={item.kind === 'error' ? 'alert' : 'status'}
            className={`pointer-events-auto rounded-md border border-ink-line bg-ink px-4 py-3 text-[13.5px] shadow-[0_10px_28px_-8px_rgba(28,27,22,0.24)] ${TOAST_TONES[item.kind]}`}
          >
            {item.text}
          </div>
        ))}
      </div>
    </FeedbackContext.Provider>
  )
}

export function useFeedback(): FeedbackValue {
  const value = useContext(FeedbackContext)
  if (!value) throw new Error('useFeedback must be used inside FeedbackProvider')
  return value
}
