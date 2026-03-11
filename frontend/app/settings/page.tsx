'use client'

import { useState, useEffect, type FormEvent, Suspense } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { isLoggedIn, clearToken } from '@/lib/auth'
import { logout } from '@/lib/api'
import { saveKey, hasKey, deleteKey } from '@/lib/crypto'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'

function SettingsContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const isNewUser = searchParams.get('new') === '1'

  const [keyExists, setKeyExists] = useState(false)
  const [apiKey, setApiKey] = useState('')
  const [password, setPassword] = useState('')
  const [maskedSuffix, setMaskedSuffix] = useState<string | null>(null)
  const [status, setStatus] = useState<'idle' | 'saving' | 'saved' | 'error' | 'deleting' | 'logging-out'>('idle')
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace('/login')
      return
    }

    hasKey().then((exists) => {
      setKeyExists(exists)
    })
  }, [router])

  async function handleSave(e: FormEvent) {
    e.preventDefault()
    setErrorMsg(null)

    if (!apiKey.startsWith('sk-') || apiKey.length < 20) {
      setErrorMsg('API key must start with "sk-" and be at least 20 characters.')
      return
    }
    if (password.length < 8) {
      setErrorMsg('Password must be at least 8 characters.')
      return
    }

    setStatus('saving')

    try {
      await saveKey(apiKey, password)
      const lastFour = apiKey.slice(-4)
      setMaskedSuffix(lastFour)
      setKeyExists(true)
      setApiKey('')
      setPassword('')
      setStatus('saved')
    } catch {
      setErrorMsg('Failed to save key. Please try again.')
      setStatus('error')
    }
  }

  async function handleDelete() {
    setStatus('deleting')
    try {
      await deleteKey()
      setKeyExists(false)
      setMaskedSuffix(null)
      setStatus('idle')
    } catch {
      setErrorMsg('Failed to delete key.')
      setStatus('idle')
    }
  }

  async function handleLogout() {
    setStatus('logging-out')
    try {
      await logout()
    } catch {
      // ignore errors, just clear local state
    } finally {
      clearToken()
      router.push('/login')
    }
  }

  return (
    <div className="min-h-screen bg-neutral-50 px-4 py-12">
      <div className="mx-auto max-w-lg">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-2xl font-bold tracking-tight text-neutral-900">Settings</h1>
          <Link
            href="/dashboard"
            className="text-sm text-neutral-500 hover:text-neutral-900 hover:underline"
          >
            Back to Dashboard
          </Link>
        </div>

        {isNewUser && (
          <div className="mb-6 rounded-md bg-blue-50 border border-blue-200 px-4 py-3 text-sm text-blue-800">
            Welcome to AgentFlow! Please enter your OpenAI API key to start running tasks.
          </div>
        )}

        <Card>
          <CardHeader>
            <CardTitle>OpenAI API Key</CardTitle>
            <CardDescription>
              Used to run your tasks. The key is stored encrypted only in your browser.
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-6">
            {/* Current key status */}
            <div className="rounded-md border border-neutral-200 bg-neutral-50 px-4 py-3">
              {keyExists ? (
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-neutral-700">
                      Status:{' '}
                      <span className="text-green-600">
                        Key saved {maskedSuffix ? `(ending in ${maskedSuffix})` : ''}
                      </span>
                    </p>
                    <p className="mt-0.5 text-xs text-neutral-400">
                      {'•'.repeat(12)}
                      {maskedSuffix ?? '????'}
                    </p>
                  </div>
                  <Button
                    variant="destructive"
                    size="sm"
                    loading={status === 'deleting'}
                    onClick={handleDelete}
                  >
                    Delete key
                  </Button>
                </div>
              ) : (
                <p className="text-sm text-neutral-500">No key configured</p>
              )}
            </div>

            {/* Save new key form */}
            <form onSubmit={handleSave} className="space-y-4">
              <h3 className="text-sm font-semibold text-neutral-800">
                {keyExists ? 'Replace key' : 'Add key'}
              </h3>

              {errorMsg && (
                <div className="rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
                  {errorMsg}
                </div>
              )}

              {status === 'saved' && (
                <div className="rounded-md bg-green-50 border border-green-200 px-4 py-3 text-sm text-green-700">
                  Key saved successfully.
                </div>
              )}

              <div className="space-y-2">
                <label htmlFor="apiKey" className="text-sm font-medium text-neutral-700">
                  OpenAI API Key
                </label>
                <Input
                  id="apiKey"
                  type="password"
                  placeholder="sk-..."
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-2">
                <label htmlFor="password" className="text-sm font-medium text-neutral-700">
                  Your login password (used to encrypt the key)
                </label>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>

              <Button type="submit" loading={status === 'saving'}>
                Save key
              </Button>
            </form>

            {/* Security disclosure */}
            <div className="rounded-md bg-blue-50 border border-blue-100 px-4 py-3 text-xs text-blue-700 leading-relaxed">
              Your key is stored only in your browser. It is sent to our server only when starting a
              task, over an encrypted connection, and is never saved.
            </div>
          </CardContent>
        </Card>

        {/* Account / logout */}
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>Account</CardTitle>
            <CardDescription>Sign out of AgentFlow on this device.</CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              variant="outline"
              loading={status === 'logging-out'}
              onClick={handleLogout}
            >
              Sign out
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default function SettingsPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-neutral-50" />}>
      <SettingsContent />
    </Suspense>
  )
}
