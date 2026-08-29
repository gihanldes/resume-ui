import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { usePageTitle } from '../lib/usePageTitle'
import { Button, Field, Input, Notice } from '../components/ui'
import { PasswordInput } from '../components/PasswordInput'

export function SignIn() {
  usePageTitle('Sign in')
  const { signIn } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [emailError, setEmailError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await signIn(email, password)
      navigate('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not sign in.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthShell
      title="Sign in"
      caption="Pick up where you left off."
      footer={
        <>
          No account yet? <Link to="/signup" className="text-ink-text underline underline-offset-4">Create one</Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <Notice tone="error">{error}</Notice>}
        <Field label="Email" error={emailError ?? undefined}>
          <Input
            type="email"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value)
              if (emailError) setEmailError(null)
            }}
            onBlur={() => setEmailError(email && !/\S+@\S+\.\S+/.test(email) ? 'That does not look like an email address.' : null)}
            required
            autoComplete="email"
            autoFocus
          />
        </Field>
        <Field label="Password">
          <PasswordInput
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
        </Field>
        <Button type="submit" loading={busy} className="w-full">
          Sign in
        </Button>
      </form>
    </AuthShell>
  )
}

export function AuthShell({
  title,
  caption,
  children,
  footer,
}: {
  title: string
  caption: string
  children: React.ReactNode
  footer: React.ReactNode
}) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-5 py-12">
      <div className="w-full max-w-sm">
        <div className="mb-8">
          <h1 className="text-4xl leading-none font-extrabold tracking-tight text-ink-text">Proof<span className="text-brand">.</span></h1>
          <p className="mt-3 text-sm leading-relaxed text-ink-muted">
            See your resume the way a recruiter reads it, and the way a parser reads it. The two
            are rarely the same.
          </p>
        </div>

        <div className="border-t border-ink-text pt-6">
          <h2 className="font-display text-xl text-ink-text">{title}</h2>
          <p className="mt-1 mb-5 text-sm text-ink-muted">{caption}</p>
          {children}
        </div>

        <p className="mt-5 text-center text-sm text-ink-muted">{footer}</p>
      </div>
    </div>
  )
}
