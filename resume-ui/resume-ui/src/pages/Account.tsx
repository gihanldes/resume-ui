import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { useFeedback } from '../components/feedback'
import { Button, Field, Input, Notice } from '../components/ui'
import { usePageTitle } from '../lib/usePageTitle'

export function Account() {
  usePageTitle('Account')
  const { user, updateUser, health, signOut } = useAuth()
  const { toast, confirm } = useFeedback()
  const navigate = useNavigate()

  const [profile, setProfile] = useState({ full_name: '', target_role: '' })
  const [savingProfile, setSavingProfile] = useState(false)

  const [passwords, setPasswords] = useState({ current_password: '', new_password: '' })
  const [passwordMsg, setPasswordMsg] = useState<{ tone: 'success' | 'error'; text: string } | null>(
    null,
  )
  const [savingPassword, setSavingPassword] = useState(false)

  const [deletePassword, setDeletePassword] = useState('')
  const [deleting, setDeleting] = useState(false)

  const [revoking, setRevoking] = useState(false)

  useEffect(() => {
    if (user) {
      setProfile({ full_name: user.full_name ?? '', target_role: user.target_role ?? '' })
    }
  }, [user])

  async function saveProfile(event: FormEvent) {
    event.preventDefault()
    setSavingProfile(true)
    try {
      updateUser(
        await api.updateMe({
          full_name: profile.full_name || null,
          target_role: profile.target_role || null,
        }),
      )
      toast('success', 'Profile saved.')
    } catch (err) {
      toast('error', err instanceof Error ? err.message : 'Could not save your profile.')
    } finally {
      setSavingProfile(false)
    }
  }

  async function savePassword(event: FormEvent) {
    event.preventDefault()
    setSavingPassword(true)
    setPasswordMsg(null)
    try {
      const result = await api.changePassword(passwords.current_password, passwords.new_password)
      setPasswords({ current_password: '', new_password: '' })
      setPasswordMsg({ tone: 'success', text: result.detail })
    } catch (err) {
      setPasswordMsg({
        tone: 'error',
        text: err instanceof Error ? err.message : 'Could not change your password.',
      })
    } finally {
      setSavingPassword(false)
    }
  }

  async function signOutOthers() {
    const confirmed = await confirm({
      title: 'Sign out other devices?',
      body: 'Every session except this one is signed out immediately.',
      confirmLabel: 'Sign out others',
    })
    if (!confirmed) return
    setRevoking(true)
    try {
      const result = await api.logoutOthers()
      toast('success', result.detail)
    } catch (err) {
      toast('error', err instanceof Error ? err.message : 'Could not sign out other sessions.')
    } finally {
      setRevoking(false)
    }
  }

  async function deleteAccount(event: FormEvent) {
    event.preventDefault()
    const confirmed = await confirm({
      title: 'Delete your account?',
      body: 'Every resume and review you have uploaded is permanently deleted. There is no recovery.',
      confirmLabel: 'Delete everything',
      danger: true,
    })
    if (!confirmed) return
    setDeleting(true)
    try {
      await api.deleteAccount(deletePassword)
      await signOut()
      navigate('/')
    } catch (err) {
      toast('error', err instanceof Error ? err.message : 'Could not delete the account.')
      setDeleting(false)
    }
  }

  return (
    <div className="max-w-2xl space-y-8">
      <header>
        <h1 className="text-[26px] leading-tight">Account</h1>
        <p className="mt-1.5 font-mono text-xs text-ink-muted">{user?.email}</p>
      </header>

      <section className="border-t border-ink-line pt-6">
        <h2 className="section-title">Profile</h2>
        <form onSubmit={saveProfile} className="mt-5 space-y-5">
          <Field label="Name">
            <Input
              value={profile.full_name}
              onChange={(e) => setProfile((p) => ({ ...p, full_name: e.target.value }))}
              autoComplete="name"
            />
          </Field>
          <Field label="Target role" hint="Pre-filled when you set up a new review.">
            <Input
              value={profile.target_role}
              onChange={(e) => setProfile((p) => ({ ...p, target_role: e.target.value }))}
              placeholder="Senior Backend Engineer"
            />
          </Field>
          <Button type="submit" loading={savingProfile}>
            Save profile
          </Button>
        </form>
      </section>

      <section className="border-t border-ink-line pt-6">
        <h2 className="section-title">Password</h2>
        <p className="mt-2 text-sm text-ink-muted">
          Changing your password signs out every other session.
        </p>
        <form onSubmit={savePassword} className="mt-5 space-y-5">
          {passwordMsg && <Notice tone={passwordMsg.tone}>{passwordMsg.text}</Notice>}
          <Field label="Current password">
            <Input
              type="password"
              value={passwords.current_password}
              onChange={(e) => setPasswords((p) => ({ ...p, current_password: e.target.value }))}
              required
              autoComplete="current-password"
            />
          </Field>
          <Field label="New password" hint="At least 10 characters, with an uppercase letter and a digit.">
            <Input
              type="password"
              value={passwords.new_password}
              onChange={(e) => setPasswords((p) => ({ ...p, new_password: e.target.value }))}
              required
              minLength={10}
              autoComplete="new-password"
            />
          </Field>
          <Button type="submit" loading={savingPassword}>
            Change password
          </Button>
        </form>
      </section>

      <section className="border-t border-ink-line pt-6">
        <h2 className="section-title">Sessions</h2>
        <p className="mt-2 max-w-[560px] text-sm leading-relaxed text-ink-muted">
          Signed in somewhere you don't recognise? This signs out every other device and keeps
          this one.
        </p>
        <div className="mt-4">
          <Button variant="ghost" loading={revoking} onClick={() => void signOutOthers()}>
            Sign out other devices
          </Button>
        </div>
      </section>

      <section className="border-t border-ink-line pt-6">
        <h2 className="section-title">Server</h2>
        <dl className="mt-4 space-y-2.5 text-sm">
          {[
            ['Engine', health ? `v${health.engine_version}` : '…'],
            ['AI review', health?.ai_available ? `on · ${health.ai_model}` : 'off'],
            ['Environment', health?.environment ?? '…'],
          ].map(([label, value]) => (
            <div
              key={label}
              className="flex items-baseline gap-3 border-b border-ink-line pb-2.5 last:border-0"
            >
              <dt className="w-28 shrink-0 font-mono text-[11px] tracking-wider text-ink-muted uppercase">
                {label}
              </dt>
              <dd className="text-ink-text">{value}</dd>
            </div>
          ))}
        </dl>
        {!health?.ai_available && (
          <p className="mt-4 text-xs leading-relaxed text-ink-muted">
            The AI review is off because the server has no OPENAI_API_KEY. Scores and findings come
            from the rule engine either way. The AI layer only adds written critique and rewrites.
          </p>
        )}
      </section>

      <section className="border-t border-ink-line pt-6">
        <h2 className="section-title text-[color:var(--color-mark-critical)]">Danger zone</h2>
        <p className="mt-2 text-sm leading-relaxed text-ink-muted">
          Deleting your account removes every resume and review permanently. Resumes are personal
          data. When you leave, nothing stays behind.
        </p>
        <form onSubmit={deleteAccount} className="mt-5 space-y-4">
          <Field label="Confirm with your password">
            <Input
              type="password"
              value={deletePassword}
              onChange={(e) => setDeletePassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </Field>
          <Button type="submit" variant="danger" loading={deleting} disabled={!deletePassword}>
            Delete my account
          </Button>
        </form>
      </section>
    </div>
  )
}
