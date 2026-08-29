import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { api, hasSession, setSignOutHandler, setTokens } from '../api/client'
import type { Health, User } from '../types'

interface AuthValue {
  user: User | null
  health: Health | null
  loading: boolean
  signIn: (email: string, password: string) => Promise<void>
  signUp: (payload: {
    email: string
    password: string
    full_name?: string
    target_role?: string
  }) => Promise<void>
  signOut: () => Promise<void>
  updateUser: (user: User) => void
}

const AuthContext = createContext<AuthValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [health, setHealth] = useState<Health | null>(null)
  const [loading, setLoading] = useState(true)

  const clearSession = useCallback(() => {
    setTokens(null)
    setUser(null)
  }, [])

  useEffect(() => {
    setSignOutHandler(clearSession)
  }, [clearSession])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      // The health call tells the UI whether the AI layer is even available.
      api
        .health()
        .then((h) => !cancelled && setHealth(h))
        .catch(() => undefined)

      if (!hasSession()) {
        if (!cancelled) setLoading(false)
        return
      }
      try {
        const me = await api.me()
        if (!cancelled) setUser(me)
      } catch {
        if (!cancelled) clearSession()
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [clearSession])

  const signIn = useCallback(async (email: string, password: string) => {
    setTokens(await api.login(email, password))
    setUser(await api.me())
  }, [])

  const signUp = useCallback<AuthValue['signUp']>(async (payload) => {
    setTokens(await api.register(payload))
    setUser(await api.me())
  }, [])

  const signOut = useCallback(async () => {
    try {
      await api.logout()
    } catch {
      /* signing out locally is what matters */
    }
    clearSession()
  }, [clearSession])

  const value = useMemo(
    () => ({ user, health, loading, signIn, signUp, signOut, updateUser: setUser }),
    [user, health, loading, signIn, signUp, signOut],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthValue {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used inside AuthProvider')
  return value
}
