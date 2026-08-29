import { useState, type InputHTMLAttributes } from 'react'
import { Input } from './ui'

/** A password field with a show/hide toggle. */
export function PasswordInput(props: InputHTMLAttributes<HTMLInputElement>) {
  const [visible, setVisible] = useState(false)
  return (
    <div className="relative">
      <Input {...props} type={visible ? 'text' : 'password'} className="pr-12" />
      <button
        type="button"
        onClick={() => setVisible((value) => !value)}
        aria-label={visible ? 'Hide password' : 'Show password'}
        className="absolute inset-y-0 right-0 flex w-11 items-center justify-center text-ink-dim transition-colors hover:text-ink-text"
      >
        {visible ? (
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
            <path d="M2 9s2.5-4.5 7-4.5S16 9 16 9s-2.5 4.5-7 4.5S2 9 2 9Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
            <circle cx="9" cy="9" r="2" stroke="currentColor" strokeWidth="1.5" />
            <path d="M3 15 15 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        ) : (
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
            <path d="M2 9s2.5-4.5 7-4.5S16 9 16 9s-2.5 4.5-7 4.5S2 9 2 9Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
            <circle cx="9" cy="9" r="2" stroke="currentColor" strokeWidth="1.5" />
          </svg>
        )}
      </button>
    </div>
  )
}
