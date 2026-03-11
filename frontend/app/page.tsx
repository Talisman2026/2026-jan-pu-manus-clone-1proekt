import { redirect } from 'next/navigation'

// Root page: server-side redirect to dashboard.
// The dashboard page itself will redirect to /login if the user is not
// authenticated (detected client-side after the token check).
export default function RootPage() {
  redirect('/dashboard')
}
