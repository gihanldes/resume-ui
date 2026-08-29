import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { usePageTitle } from '../lib/usePageTitle'
import { Button, Field, Input, Notice } from '../components/ui'
import { PasswordInput } from '../components/PasswordInput'
import { AuthShell } from './SignIn'

export function SignUp() {
  usePageTitle('Create account')
  const { signUp } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', password: '', full_name: '', target_role: '' })
  const [error, setError] = useState<string | null>(null)
  const [emailError, setEmailError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((prev) => ({ ...prev, [key]: e.target.value }))

  const checks = [
    { ok: form.password.length >= 10, label: '10+ characters' },
    { ok: /[A-Z]/.test(form.password), label: 'an uppercase letter' },
    { ok: /\d/.test(form.password), label: 'a digit' },
  ]

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await signUp({
        email: form.email,
        password: form.password,
        full_name: form.full_name || undefined,
        target_role: form.target_role || undefined,
      })
      navigate('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create the account.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthShell
      title="Create an account"
      caption="Your resumes and past reviews stay in your account."
      footer={
        <>
          Already have one? <Link to="/signin" className="text-ink-text underline underline-offset-4">Sign in</Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <Notice tone="error">{error}</Notice>}
        <Field label="Email" error={emailError ?? undefined}>
          <Input
            type="email"
            value={form.email}
            onChange={(e) => {
              set('email')(e)
              if (emailError) setEmailError(null)
            }}
            onBlur={() => setEmailError(form.email && !/\S+@\S+\.\S+/.test(form.email) ? 'That does not look like an email address.' : null)}
            required
            autoComplete="email"
            autoFocus
          />
        </Field>
        <Field label="Password" hint={undefined}>
          <PasswordInput
            value={form.password}
            onChange={set('password')}
            required
            minLength={10}
            autoComplete="new-password"
          />
          <p className="mt-1.5 text-xs text-ink-muted">
            {checks.map((check, index) => (
              <span key={check.label} style={{ color: check.ok ? 'var(--color-mark-positive)' : undefined }}>
                {index > 0 && ' · '}
                {check.ok ? '✓ ' : ''}{check.label}
              </span>
            ))}
          </p>
        </Field>
        <Field label="Name" hint="Optional.">
          <Input value={form.full_name} onChange={set('full_name')} autoComplete="name" />
        </Field>
        <Field label="Target role" hint="Optional. Used as the default when you run a review.">
          <Input
            value={form.target_role}
            onChange={set('target_role')}
            placeholder="Senior Backend Engineer"
          />
        </Field>
        <Button type="submit" loading={busy} className="w-full">
          Create account
        </Button>
      </form>
    </AuthShell>
  )
}
