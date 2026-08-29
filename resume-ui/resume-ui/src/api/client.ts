/**
 * Thin API client. Holds the token pair, refreshes an expired access token
 * once per request, and surfaces server messages verbatim so the UI can show
 * what actually went wrong.
 */
import type {
  Analysis,
  AnalysisSummary,
  CompareResult,
  Health,
  Resume,
  ResumeDetail,
  Stats,
  TokenPair,
  User,
} from '../types'

const BASE = '/api'
const STORAGE_KEY = 'proof.tokens'

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

let tokens: TokenPair | null = null
let onSignOut: (() => void) | null = null

function load(): TokenPair | null {
  if (tokens) return tokens
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    tokens = raw ? (JSON.parse(raw) as TokenPair) : null
  } catch {
    tokens = null
  }
  return tokens
}

export function setTokens(next: TokenPair | null): void {
  tokens = next
  try {
    if (next) localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
    else localStorage.removeItem(STORAGE_KEY)
  } catch {
    /* storage can be unavailable in private mode; the session still works */
  }
}

export function hasSession(): boolean {
  return load() !== null
}

export function setSignOutHandler(handler: () => void): void {
  onSignOut = handler
}

async function readError(response: Response): Promise<string> {
  try {
    const body = await response.json()
    if (typeof body?.detail === 'string') return body.detail
    if (Array.isArray(body?.detail) && body.detail[0]?.msg) return String(body.detail[0].msg)
  } catch {
    /* fall through to the status text */
  }
  return response.statusText || `Request failed (${response.status})`
}

let refreshing: Promise<boolean> | null = null

async function refreshTokens(): Promise<boolean> {
  const current = load()
  if (!current?.refresh_token) return false
  // Collapse concurrent 401s into a single refresh.
  refreshing ??= (async () => {
    try {
      const response = await fetch(`${BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: current.refresh_token }),
      })
      if (!response.ok) return false
      setTokens((await response.json()) as TokenPair)
      return true
    } catch {
      return false
    } finally {
      refreshing = null
    }
  })()
  return refreshing
}

interface RequestOptions {
  method?: string
  body?: unknown
  form?: FormData
  auth?: boolean
  retry?: boolean
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, form, auth = true, retry = true } = options
  const headers: Record<string, string> = {}
  const current = load()

  if (auth && current) headers.Authorization = `Bearer ${current.access_token}`
  if (body !== undefined) headers['Content-Type'] = 'application/json'

  const response = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: form ?? (body !== undefined ? JSON.stringify(body) : undefined),
  })

  if (response.status === 401 && auth && retry) {
    if (await refreshTokens()) {
      return request<T>(path, { ...options, retry: false })
    }
    setTokens(null)
    onSignOut?.()
    throw new ApiError('Your session has expired. Sign in again.', 401)
  }

  if (!response.ok) throw new ApiError(await readError(response), response.status)
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export const api = {
  health: () => request<Health>('/health', { auth: false }),

  register: (payload: {
    email: string
    password: string
    full_name?: string
    target_role?: string
  }) => request<TokenPair>('/auth/register', { method: 'POST', body: payload, auth: false }),

  login: (email: string, password: string) =>
    request<TokenPair>('/auth/login', {
      method: 'POST',
      body: { email, password },
      auth: false,
    }),

  logout: () => request<{ detail: string }>('/auth/logout', { method: 'POST' }),

  me: () => request<User>('/auth/me'),

  updateMe: (payload: { full_name?: string | null; target_role?: string | null }) =>
    request<User>('/auth/me', { method: 'PATCH', body: payload }),

  changePassword: (current_password: string, new_password: string) =>
    request<{ detail: string }>('/auth/change-password', {
      method: 'POST',
      body: { current_password, new_password },
    }),

  logoutOthers: () =>
    request<{ detail: string }>('/auth/logout-others', {
      method: 'POST',
      body: { refresh_token: load()?.refresh_token ?? '' },
    }),

  uploadResume: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<Resume>('/resumes', { method: 'POST', form })
  },

  listResumes: () => request<Resume[]>('/resumes'),
  getResume: (id: string) => request<ResumeDetail>(`/resumes/${id}`),
  deleteResume: (id: string) => request<{ detail: string }>(`/resumes/${id}`, { method: 'DELETE' }),

  renameResume: (id: string, filename: string) =>
    request<Resume>(`/resumes/${id}`, { method: 'PATCH', body: { filename } }),

  analyze: (
    resumeId: string,
    payload: { target_role?: string | null; job_description?: string | null; include_ai: boolean },
  ) => request<Analysis>(`/resumes/${resumeId}/analyze`, { method: 'POST', body: payload }),

  listAnalyses: (params?: { limit?: number; resume_id?: string }) => {
    const query = new URLSearchParams()
    if (params?.limit) query.set('limit', String(params.limit))
    if (params?.resume_id) query.set('resume_id', params.resume_id)
    const suffix = query.toString() ? `?${query}` : ''
    return request<AnalysisSummary[]>(`/analyses${suffix}`)
  },

  getAnalysis: (id: string) => request<Analysis>(`/analyses/${id}`),
  deleteAnalysis: (id: string) =>
    request<{ detail: string }>(`/analyses/${id}`, { method: 'DELETE' }),

  stats: () => request<Stats>('/stats'),

  compare: (analysisId: string, withId?: string) =>
    request<CompareResult>(
      `/analyses/${analysisId}/compare${withId ? `?with=${encodeURIComponent(withId)}` : ''}`,
    ),

  runAIReview: (analysisId: string) =>
    request<Analysis>(`/analyses/${analysisId}/ai`, { method: 'POST' }),

  deleteAccount: (password: string) =>
    request<{ detail: string }>('/auth/me', { method: 'DELETE', body: { password } }),
}
