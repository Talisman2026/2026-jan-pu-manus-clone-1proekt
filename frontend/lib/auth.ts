// JWT token is stored in memory (module-level) only.
// The backend sets an httpOnly cookie for the refresh token.
// Access token lives in memory so it survives page navigation within the same
// browser tab session but is lost on hard refresh (user must log in again).

let _token: string | null = null

export function getToken(): string | null {
  return _token
}

export function setToken(token: string): void {
  _token = token
}

export function clearToken(): void {
  _token = null
}

export function isLoggedIn(): boolean {
  return _token !== null
}
