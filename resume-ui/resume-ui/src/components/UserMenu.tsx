import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

function initials(name: string | null | undefined, email: string | undefined): string {
  const source = name?.trim() || email?.split('@')[0] || '??'
  const parts = source.split(/[\s._-]+/).filter(Boolean)
  const letters = parts.length >= 2 ? `${parts[0][0]}${parts[1][0]}` : source.slice(0, 2)
  return letters.toUpperCase()
}

/** Initials avatar opening the account dropdown. Esc, outside click and route
 *  changes close it; focus returns to the trigger. */
export function UserMenu() {
  const { user, health, signOut } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)

  useEffect(() => setOpen(false), [location.pathname])

  useEffect(() => {
    if (!open) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpen(false)
        triggerRef.current?.focus()
      }
    }
    const onClick = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false)
    }
    window.addEventListener('keydown', onKey)
    window.addEventListener('mousedown', onClick)
    return () => {
      window.removeEventListener('keydown', onKey)
      window.removeEventListener('mousedown', onClick)
    }
  }, [open])

  const itemClass =
    'block w-full px-4 py-2 text-left text-sm text-ink-text transition-colors hover:bg-well'

  return (
    <div ref={rootRef} className="relative">
      <button
        ref={triggerRef}
        type="button"
        aria-expanded={open}
        aria-label="Account menu"
        onClick={() => setOpen((value) => !value)}
        className="flex size-9 items-center justify-center rounded-full bg-brand text-[12.5px] font-bold tracking-wide text-[#fbfaf7] transition-colors hover:bg-brand-deep"
      >
        {initials(user?.full_name, user?.email)}
      </button>

      {open && (
        <div
          aria-label="Account"
          className="absolute right-0 top-11 z-30 w-64 rounded-md border border-ink-line bg-ink py-1.5 shadow-[0_10px_30px_rgba(28,27,22,0.12)]"
        >
          <div className="border-b border-ink-faint px-4 pt-1.5 pb-2.5">
            <p className="truncate text-sm font-semibold text-ink-text">
              {user?.full_name || 'Your account'}
            </p>
            <p className="truncate text-[12.5px] text-ink-muted">{user?.email}</p>
          </div>
          <div className="py-1">
            <Link to="/account" className={itemClass}>
              Account
            </Link>
            <Link to="/how-it-works" className={itemClass}>
              How scoring works
            </Link>
          </div>
          <div className="border-t border-ink-faint px-4 py-2 text-[12.5px] text-ink-muted">
            {health?.ai_available ? `AI review on · ${health.ai_model}` : 'AI review off'}
          </div>
          <div className="border-t border-ink-faint py-1">
            <button
              type="button"
              className={itemClass}
              onClick={async () => {
                await signOut()
                navigate('/')
              }}
            >
              Sign out
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
