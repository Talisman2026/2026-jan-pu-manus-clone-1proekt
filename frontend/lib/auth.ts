// JWT token is stored in sessionStorage so it survives Next.js client-side
// route navigation and soft refreshes within the same browser tab.
// It is cleared when the tab is closed.

const SESSION_KEY = 'agentflow_token'

export function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return sessionStorage.getItem(SESSION_KEY)
}

export function setToken(token: string): void {
  if (typeof window !== 'undefined') {
    sessionStorage.setItem(SESSION_KEY, token)
  }
}

export function clearToken(): void {
  if (typeof window !== 'undefined') {
    sessionStorage.removeItem(SESSION_KEY)
  }
}

export function isLoggedIn(): boolean {
  return getToken() !== null
}
