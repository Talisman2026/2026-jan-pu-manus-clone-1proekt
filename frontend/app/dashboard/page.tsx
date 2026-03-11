'use client'

import { useState, useEffect, type FormEvent } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { isLoggedIn, clearToken } from '@/lib/auth'
import { hasKey, loadKey } from '@/lib/crypto'
import { getTasks, createTask, runTask, ApiError } from '@/lib/api'
import type { TaskListItem, CreateTaskResponse } from '@/lib/types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'
import { TaskCard } from '@/components/task-card'

export default function DashboardPage() {
  const router = useRouter()

  const [tasks, setTasks] = useState<TaskListItem[]>([])
  const [loadingTasks, setLoadingTasks] = useState(true)
  const [fetchError, setFetchError] = useState<string | null>(null)

  // New task form state
  const [showForm, setShowForm] = useState(false)
  const [description, setDescription] = useState('')
  const [estimating, setEstimating] = useState(false)
  const [estimation, setEstimation] = useState<CreateTaskResponse | null>(null)
  const [budgetCap, setBudgetCap] = useState<string>('2.00')
  const [formError, setFormError] = useState<string | null>(null)

  // Run task state
  const [running, setRunning] = useState(false)
  const [needsKey, setNeedsKey] = useState(false)
  const [passwordPrompt, setPasswordPrompt] = useState('')
  const [passwordError, setPasswordError] = useState<string | null>(null)

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace('/login')
      return
    }
    fetchTasks()
  }, [router])

  async function fetchTasks() {
    setLoadingTasks(true)
    setFetchError(null)
    try {
      const data = await getTasks()
      setTasks(data)
    } catch (err) {
      setFetchError(err instanceof Error ? err.message : 'Failed to load tasks.')
    } finally {
      setLoadingTasks(false)
    }
  }

  function handleNewTask() {
    setShowForm((v) => !v)
    setEstimation(null)
    setDescription('')
    setBudgetCap('2.00')
    setFormError(null)
  }

  async function handleEstimate(e: FormEvent) {
    e.preventDefault()
    setFormError(null)
    setEstimation(null)

    if (!description.trim()) {
      setFormError('Please enter a task description.')
      return
    }

    setEstimating(true)
    try {
      const res = await createTask(description.trim())
      setEstimation(res)
      if (res.estimation) {
        const suggested = (res.estimation.cost_estimate_usd * 2).toFixed(2)
        const capped = Math.min(20, Math.max(0.1, parseFloat(suggested)))
        setBudgetCap(capped.toFixed(2))
      }
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Estimation failed.')
    } finally {
      setEstimating(false)
    }
  }

  async function handleRun(e: FormEvent) {
    e.preventDefault()
    setFormError(null)
    setPasswordError(null)

    if (!estimation) return

    const keyExists = await hasKey()
    if (!keyExists) {
      setNeedsKey(true)
      return
    }

    setRunning(true)

    const apiKey = await loadKey(passwordPrompt)
    if (!apiKey) {
      setPasswordError('Wrong password or no key stored. Please check your password.')
      setRunning(false)
      return
    }

    const budget = parseFloat(budgetCap)
    if (isNaN(budget) || budget < 0.1 || budget > 20) {
      setFormError('Budget cap must be between $0.10 and $20.00.')
      setRunning(false)
      return
    }

    try {
      await runTask(estimation.id, { budget_cap: budget, openai_key: apiKey })
      router.push(`/task/${estimation.id}`)
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setFormError('You already have an active task. Wait for it to finish before starting a new one.')
      } else {
        setFormError(err instanceof Error ? err.message : 'Failed to start task.')
      }
      setRunning(false)
    }
  }

  function handleLogout() {
    clearToken()
    router.push('/login')
  }

  return (
    <div className="min-h-screen bg-neutral-50">
      {/* Header */}
      <header className="border-b border-neutral-200 bg-white">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-4">
          <h1 className="text-xl font-bold tracking-tight text-neutral-900">AgentFlow</h1>
          <div className="flex items-center gap-3">
            <Link
              href="/settings"
              className="text-sm text-neutral-500 hover:text-neutral-900 hover:underline"
            >
              Settings
            </Link>
            <Button variant="ghost" size="sm" onClick={handleLogout}>
              Sign out
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 py-8">
        {/* Page title + new task button */}
        <div className="mb-6 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-neutral-800">Your Tasks</h2>
          <Button size="sm" onClick={handleNewTask}>
            {showForm ? 'Cancel' : '+ New Task'}
          </Button>
        </div>

        {/* New task form */}
        {showForm && (
          <Card className="mb-6">
            <CardContent className="pt-6 space-y-4">
              <h3 className="font-semibold text-neutral-800">Create a new task</h3>

              {formError && (
                <div className="rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
                  {formError}
                </div>
              )}

              {/* Step 1: description + estimate */}
              {!estimation && (
                <form onSubmit={handleEstimate} className="space-y-4">
                  <div className="space-y-2">
                    <label htmlFor="desc" className="text-sm font-medium text-neutral-700">
                      Task description
                    </label>
                    <textarea
                      id="desc"
                      rows={4}
                      maxLength={2000}
                      placeholder="Describe your task — e.g. 'Research the top 5 open-source LLM frameworks in 2025 and summarise their pros and cons.'"
                      className="w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm placeholder:text-neutral-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neutral-900 focus-visible:ring-offset-2 resize-none"
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      required
                    />
                    <p className="text-right text-xs text-neutral-400">
                      {description.length} / 2000
                    </p>
                  </div>
                  <Button type="submit" loading={estimating}>
                    Estimate
                  </Button>
                </form>
              )}

              {/* Step 2: show estimation + run */}
              {estimation && (
                <form onSubmit={handleRun} className="space-y-4">
                  <div className="rounded-md bg-neutral-50 border border-neutral-200 px-4 py-3 text-sm text-neutral-700">
                    <p className="font-medium text-neutral-800 mb-1">Estimation</p>
                    {estimation.estimation ? (
                      <>
                        <p>
                          <span className="text-neutral-500">Steps:</span>{' '}
                          {estimation.estimation.steps}
                        </p>
                        <p>
                          <span className="text-neutral-500">Duration:</span>{' '}
                          {estimation.estimation.duration_min}–{estimation.estimation.duration_max} min
                        </p>
                        <p>
                          <span className="text-neutral-500">Est. cost:</span>{' '}
                          ~${estimation.estimation.cost_estimate_usd.toFixed(4)}
                        </p>
                      </>
                    ) : (
                      <p className="text-neutral-400">Estimation unavailable</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <label htmlFor="budget" className="text-sm font-medium text-neutral-700">
                      Budget cap ($)
                    </label>
                    <Input
                      id="budget"
                      type="number"
                      min="0.10"
                      max="20.00"
                      step="0.10"
                      value={budgetCap}
                      onChange={(e) => setBudgetCap(e.target.value)}
                      required
                    />
                    <p className="text-xs text-neutral-400">Min $0.10 — max $20.00</p>
                  </div>

                  {needsKey ? (
                    <div className="rounded-md bg-yellow-50 border border-yellow-200 px-4 py-3 text-sm text-yellow-800">
                      No OpenAI key found.{' '}
                      <Link href="/settings" className="font-medium underline">
                        Add your key in Settings
                      </Link>{' '}
                      first.
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <label htmlFor="runPassword" className="text-sm font-medium text-neutral-700">
                        Your password (to decrypt your API key)
                      </label>
                      <Input
                        id="runPassword"
                        type="password"
                        placeholder="••••••••"
                        autoComplete="current-password"
                        value={passwordPrompt}
                        onChange={(e) => {
                          setPasswordPrompt(e.target.value)
                          setPasswordError(null)
                        }}
                        error={passwordError ?? undefined}
                        required
                      />
                    </div>
                  )}

                  <div className="flex gap-3">
                    <Button type="submit" loading={running} disabled={needsKey}>
                      Run task
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => {
                        setEstimation(null)
                        setNeedsKey(false)
                        setPasswordPrompt('')
                        setPasswordError(null)
                        setFormError(null)
                      }}
                    >
                      Back
                    </Button>
                  </div>
                </form>
              )}
            </CardContent>
          </Card>
        )}

        {/* Task list */}
        {loadingTasks ? (
          <div className="flex items-center justify-center py-16 text-sm text-neutral-400">
            <svg
              className="mr-2 h-4 w-4 animate-spin"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Loading tasks...
          </div>
        ) : fetchError ? (
          <div className="rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
            {fetchError}
          </div>
        ) : tasks.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-neutral-200 bg-white py-16 text-center">
            <p className="text-neutral-500">No tasks yet.</p>
            <p className="mt-1 text-sm text-neutral-400">
              Click <span className="font-medium text-neutral-600">&quot;+ New Task&quot;</span> to create your first task.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {tasks.map((task) => (
              <TaskCard key={task.id} task={task} />
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
