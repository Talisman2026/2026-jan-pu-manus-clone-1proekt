'use client'

import { useState, useEffect, useCallback, use } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { isLoggedIn } from '@/lib/auth'
import { getTask, cancelTask, downloadTaskResult } from '@/lib/api'
import type { Task, TaskStatus } from '@/lib/types'
import { Button } from '@/components/ui/button'
import { StatusBadge } from '@/components/ui/badge'
import { BudgetBar } from '@/components/budget-bar'
import { TaskLog } from '@/components/task-log'

// budget_warning is quasi-terminal: agent is still running but will auto-stop
// soon. Keep polling but at a slower interval to show the final state.
const TERMINAL_STATUSES: TaskStatus[] = ['completed', 'failed', 'paused', 'budget_warning']
const POLL_INTERVAL_MS = 2000

export default function TaskPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const router = useRouter()

  const [task, setTask] = useState<Task | null>(null)
  const [loading, setLoading] = useState(true)
  const [fetchError, setFetchError] = useState<string | null>(null)
  const [cancelling, setCancelling] = useState(false)
  const [cancelError, setCancelError] = useState<string | null>(null)
  const [downloading, setDownloading] = useState(false)

  const isTerminal = task ? TERMINAL_STATUSES.includes(task.status) : false

  const fetchTask = useCallback(async () => {
    try {
      const data = await getTask(id)
      setTask(data)
      setFetchError(null)
    } catch (err) {
      setFetchError(err instanceof Error ? err.message : 'Failed to load task.')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace('/login')
      return
    }

    fetchTask()
  }, [fetchTask, router])

  // Polling while task is active
  useEffect(() => {
    if (isTerminal || loading) return

    const intervalId = setInterval(() => {
      fetchTask()
    }, POLL_INTERVAL_MS)

    return () => clearInterval(intervalId)
  }, [isTerminal, loading, fetchTask])

  async function handleDownload() {
    if (!task) return
    setDownloading(true)
    try {
      const blobUrl = await downloadTaskResult(task.id)
      const a = document.createElement('a')
      a.href = blobUrl
      a.download = `task-${task.id}-result`
      a.click()
      URL.revokeObjectURL(blobUrl)
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Download failed')
    } finally {
      setDownloading(false)
    }
  }

  async function handleCancel() {
    if (!task) return
    setCancelError(null)
    setCancelling(true)
    try {
      await cancelTask(task.id)
      await fetchTask()
    } catch (err) {
      setCancelError(err instanceof Error ? err.message : 'Failed to cancel task.')
    } finally {
      setCancelling(false)
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="flex items-center gap-2 text-sm text-neutral-400">
          <svg
            className="h-4 w-4 animate-spin"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Loading task...
        </div>
      </div>
    )
  }

  if (fetchError) {
    return (
      <div className="flex min-h-screen items-center justify-center px-4">
        <div className="max-w-sm text-center">
          <p className="text-sm text-red-600">{fetchError}</p>
          <Link href="/dashboard" className="mt-4 inline-block text-sm text-neutral-500 hover:underline">
            Back to Dashboard
          </Link>
        </div>
      </div>
    )
  }

  if (!task) return null

  const hasBudgetWarning = task.status === 'budget_warning'

  const isRunning = task.status === 'running' || task.status === 'estimating'

  return (
    <div className="min-h-screen bg-neutral-50">
      {/* Header */}
      <header className="border-b border-neutral-200 bg-white">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-4">
          <Link
            href="/dashboard"
            className="text-sm text-neutral-500 hover:text-neutral-900 hover:underline"
          >
            Back to Dashboard
          </Link>
          <StatusBadge status={task.status} />
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 py-8 space-y-6">
        {/* Task description */}
        <div>
          <h2 className="text-lg font-semibold text-neutral-800 leading-snug">
            {task.description.length > 200
              ? task.description.slice(0, 200) + '…'
              : task.description}
          </h2>
          <p className="mt-1 text-xs text-neutral-400">
            Created {new Date(task.created_at).toLocaleString()}
            {task.completed_at && (
              <> &mdash; Completed {new Date(task.completed_at).toLocaleString()}</>
            )}
          </p>
        </div>

        {/* Budget bar */}
        {task.budget_cap !== null && (
          <div className="rounded-lg border border-neutral-200 bg-white p-4">
            <BudgetBar cost_actual={task.cost_actual} budget_cap={task.budget_cap} />
          </div>
        )}

        {/* Budget warning banner */}
        {hasBudgetWarning && (
          <div className="rounded-md bg-yellow-50 border border-yellow-300 px-4 py-3 text-sm text-yellow-800">
            Budget warning: the agent is approaching the spending limit. It will stop automatically when the cap is reached.
          </div>
        )}

        {/* Step log */}
        <div>
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-neutral-500">
            Agent Steps
          </h3>
          <TaskLog steps={task.steps} status={task.status} />
        </div>

        {/* Result summary */}
        {task.status === 'completed' && task.result_summary && (
          <div className="rounded-lg border border-green-200 bg-green-50 p-4">
            <h3 className="mb-2 text-sm font-semibold text-green-800">Summary</h3>
            <p className="text-sm text-green-700 whitespace-pre-wrap">{task.result_summary}</p>
          </div>
        )}

        {/* Actions */}
        <div className="flex flex-wrap items-center gap-3">
          {task.has_result && (
            <Button variant="outline" loading={downloading} onClick={handleDownload}>
              Download Result
            </Button>
          )}

          {isRunning && (
            <>
              <Button
                variant="destructive"
                loading={cancelling}
                onClick={handleCancel}
              >
                Cancel Task
              </Button>
              {cancelError && (
                <p className="text-sm text-red-600">{cancelError}</p>
              )}
            </>
          )}
        </div>

        {/* Polling indicator */}
        {isRunning && (
          <div className="flex items-center gap-2 text-xs text-neutral-400">
            <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-blue-400" />
            Auto-refreshing every {POLL_INTERVAL_MS / 1000}s&hellip;
          </div>
        )}
      </main>
    </div>
  )
}
