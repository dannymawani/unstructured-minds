const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const CLERK_ENABLED = !!import.meta.env.VITE_CLERK_PUBLISHABLE_KEY

class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

// Auth token getter — set from AuthTokenSync when Clerk is enabled.
// A Promise gates all API requests until the getter is registered,
// preventing race conditions where requests fire before auth is ready.
let _getToken: (() => Promise<string | null>) | null = null
let _resolveTokenReady: () => void
const _tokenReady = new Promise<void>(resolve => { _resolveTokenReady = resolve })

// If Clerk is not enabled, resolve immediately so requests aren't blocked
if (!CLERK_ENABLED) _resolveTokenReady!()

export function setTokenGetter(fn: () => Promise<string | null>) {
  _getToken = fn
  _resolveTokenReady()
}

async function getAuthHeaders(): Promise<Record<string, string>> {
  await _tokenReady
  if (!_getToken) return {}
  const token = await _getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const authHeaders = await getAuthHeaders()
  const headers: Record<string, string> = {
    ...(init?.headers as Record<string, string>),
    ...authHeaders,
  }

  const response = await _originalFetch(`${API_BASE_URL}${path}`, { ...init, headers })
  if (!response.ok) {
    throw new ApiError(response.status, `${init?.method || 'GET'} ${path} failed: ${response.status}`)
  }
  return response.json() as Promise<T>
}

// ---------------------------------------------------------------------------
// Global fetch interceptor: automatically injects auth headers for ALL
// fetch() calls to the API, including the 50+ direct fetch() calls scattered
// across components that don't use the `api` module.
// ---------------------------------------------------------------------------
const _originalFetch = window.fetch.bind(window)
window.fetch = async function (input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const url = typeof input === 'string' ? input : input instanceof URL ? input.href : (input as Request).url
  if (url.startsWith(API_BASE_URL)) {
    const authHeaders = await getAuthHeaders()
    const headers: Record<string, string> = {
      ...(init?.headers as Record<string, string>),
      ...authHeaders,
    }
    return _originalFetch(input, { ...init, headers })
  }
  return _originalFetch(input, init)
}

export const api = {
  baseUrl: API_BASE_URL,

  get<T>(path: string): Promise<T> {
    return request<T>(path)
  },

  post<T>(path: string, body?: unknown): Promise<T> {
    return request<T>(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  },

  put<T>(path: string, body?: unknown): Promise<T> {
    return request<T>(path, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  },

  patch<T>(path: string, body?: unknown): Promise<T> {
    return request<T>(path, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  },

  delete<T>(path: string): Promise<T> {
    return request<T>(path, { method: 'DELETE' })
  },

  /** Raw fetch for streaming / SSE responses — also attaches auth headers */
  async raw(path: string, init?: RequestInit): Promise<Response> {
    const authHeaders = await getAuthHeaders()
    const headers: Record<string, string> = {
      ...(init?.headers as Record<string, string>),
      ...authHeaders,
    }
    return _originalFetch(`${API_BASE_URL}${path}`, { ...init, headers })
  },
}
