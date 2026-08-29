import { useEffect, useRef, useState } from 'react'
import { Link, NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { UserMenu } from './UserMenu'

function NavItem({
  to,
  end,
  children,
}: {
  to: string
  end?: boolean
  children: React.ReactNode
}) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `-mb-px flex items-center border-b-2 text-sm transition-colors ${
          isActive
            ? 'border-brand font-medium text-ink-text'
            : 'border-transparent text-ink-muted hover:text-ink-text'
        }`
      }
    >
      {children}
    </NavLink>
  )
}

export function Layout() {
  const { health } = useAuth()
  const [mobileOpen, setMobileOpen] = useState(false)
  const headerRef = useRef<HTMLElement>(null)
  const mobileToggleRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!mobileOpen) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setMobileOpen(false)
        mobileToggleRef.current?.focus()
      }
    }
    const onClick = (event: MouseEvent) => {
      if (!headerRef.current?.contains(event.target as Node)) setMobileOpen(false)
    }
    window.addEventListener('keydown', onKey)
    window.addEventListener('mousedown', onClick)
    return () => {
      window.removeEventListener('keydown', onKey)
      window.removeEventListener('mousedown', onClick)
    }
  }, [mobileOpen])

  return (
    <div className="flex min-h-screen flex-col">
      <header ref={headerRef} className="border-b border-ink-line">
        <div className="mx-auto flex h-[60px] w-full max-w-[984px] items-stretch gap-6 px-5 sm:gap-8 sm:px-8">
          <NavLink to="/" className="flex items-center">
            <span className="text-xl font-extrabold tracking-tight text-ink-text">
              Proof<span className="text-brand">.</span>
            </span>
          </NavLink>

          <nav className="hidden items-stretch gap-5 sm:flex sm:gap-6" aria-label="Main">
            <NavItem to="/" end>
              Home
            </NavItem>
            <NavItem to="/resumes">Resumes</NavItem>
            <NavItem to="/history">History</NavItem>
          </nav>

          <div className="ml-auto flex items-center gap-3">
            <UserMenu />
            <button
              ref={mobileToggleRef}
              type="button"
              aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
              aria-expanded={mobileOpen}
              onClick={() => setMobileOpen((value) => !value)}
              className="flex size-10 items-center justify-center text-ink-text sm:hidden"
            >
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
                {mobileOpen ? (
                  <path d="M3 3l12 12M15 3L3 15" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
                ) : (
                  <path d="M2 4.5h14M2 9h14M2 13.5h14" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
                )}
              </svg>
            </button>
          </div>
        </div>

        {mobileOpen && (
          <nav
            aria-label="Main menu"
            className="border-t border-ink-faint px-5 pt-2 pb-3 sm:hidden"
          >
            {[
              ['/', 'Home'],
              ['/resumes', 'Resumes'],
              ['/history', 'History'],
              ['/account', 'Account'],
              ['/how-it-works', 'How scoring works'],
            ].map(([to, label]) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                onClick={() => setMobileOpen(false)}
                className={({ isActive }) =>
                  `block py-2.5 text-[15px] ${
                    isActive ? 'font-semibold text-ink-text' : 'text-ink-muted'
                  }`
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>
        )}
      </header>

      <main className="mx-auto w-full max-w-[984px] flex-1 px-5 py-8 sm:px-8">
        <Outlet />
      </main>

      <footer className="border-t border-ink-line">
        <div className="mx-auto flex max-w-[984px] flex-wrap items-baseline gap-x-8 gap-y-1 px-5 py-4 text-[12.5px] text-ink-dim sm:px-8">
          <span className="min-w-0 flex-1 basis-72">
            Deterministic rule engine{health?.engine_version ? ` v${health.engine_version}` : ''}.
            Every deduction names the words that caused it.
          </span>
          <span className="flex gap-5">
            <Link to="/how-it-works" className="transition-colors hover:text-ink-text">How it works</Link>
            <Link to="/terms" className="transition-colors hover:text-ink-text">Terms</Link>
            <Link to="/privacy" className="transition-colors hover:text-ink-text">Privacy</Link>
          </span>
        </div>
      </footer>
    </div>
  )
}
