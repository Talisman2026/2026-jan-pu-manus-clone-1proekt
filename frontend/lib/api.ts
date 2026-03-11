import { getToken, clearToken } from './auth'
import type {
  Task,
  TaskListItem,
  AuthResponse,
  CreateTaskResponse,
  RunTaskRequest,
} from './types'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken()

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    credentials: 'include', // include cookies for httpOnly refresh token
  })

  if (res.status === 401) {
    clearToken()
    if (typeof window !== 'undefined') {
      window.location.href = '/login'
    }
    throw new ApiError(401, 'Unauthorized')
  }

  if (!res.ok) {
    let message = `HTTP ${res.status}`
    try {
      const body = (await res.json()) as { detail?: string }
      if (body.detail) message = body.detail
    } catch {
      // ignore parse error
    }
    throw new ApiError(res.status, message)
  }

  // 204 No Content
  if (res.status === 204) {
    return undefined as unknown as T
  }

  return res.json() as Promise<T>
}

// ─── Auth ────────────────────────────────────────────────────────────────────

export async function register(
  email: string,
  password: string
): Promise<AuthResponse> {
  return request<AuthResponse>('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
}

export async function login(
  email: string,
  password: string
): Promise<AuthResponse> {
  return request<AuthResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
}

export async function logout(): Promise<void> {
  return request<void>('/auth/logout', { method: 'POST' })
}

// ─── Tasks ───────────────────────────────────────────────────────────────────

export async function getTasks(): Promise<TaskListItem[]> {
  return request<TaskListItem[]>('/tasks')
}

export async function createTask(description: string): Promise<CreateTaskResponse> {
  return request<CreateTaskResponse>('/tasks', {
    method: 'POST',
    body: JSON.stringify({ description }),
  })
}

export async function runTask(
  taskId: string,
  payload: RunTaskRequest
): Promise<{ status: string }> {
  return request<{ status: string }>(`/tasks/${taskId}/run`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function getTask(taskId: string): Promise<Task> {
  return request<Task>(`/tasks/${taskId}`)
}

export async function cancelTask(taskId: string): Promise<void> {
  return request<void>(`/tasks/${taskId}/cancel`, { method: 'POST' })
}

/**
 * Download the task result file using the Authorization header (never in URL).
 * Returns a temporary blob URL for programmatic download.
 * Caller is responsible for revoking the URL with URL.revokeObjectURL().
 */
export async function downloadTaskResult(taskId: string): Promise<string> {
  const token = getToken()
  const res = await fetch(`${API_BASE}/tasks/${taskId}/result`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    credentials: 'include',
  })
  if (!res.ok) {
    throw new ApiError(res.status, `Download failed: HTTP ${res.status}`)
  }
  const blob = await res.blob()
  return URL.createObjectURL(blob)
}

export { ApiError }
