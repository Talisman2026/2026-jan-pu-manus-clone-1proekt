'use client'

import { useEffect, useRef } from 'react'
import { clsx } from 'clsx'
import type { TaskStep, ToolType } from '@/lib/types'

const toolIcons: Record<ToolType, string> = {
  web_search: '🔍',
  scrape_url: '🌐',
  run_python: '🐍',
  write_file: '📄',
  finish: '✅',
}

const toolLabels: Record<ToolType, string> = {
  web_search: 'Web Search',
  scrape_url: 'Scrape URL',
  run_python: 'Run Python',
  write_file: 'Write File',
  finish: 'Finish',
}

interface StepRowProps {
  step: TaskStep
}

function StepRow({ step }: StepRowProps) {
  const icon = toolIcons[step.tool] ?? '⚙️'
  const label = toolLabels[step.tool] ?? step.tool

  const statusClass =
    step.status === 'running'
      ? 'text-blue-600'
      : step.status === 'error'
        ? 'text-red-600'
        : 'text-green-600'

  const statusDot =
    step.status === 'running' ? (
      <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-blue-500" />
    ) : step.status === 'error' ? (
      <span className="inline-block h-2 w-2 rounded-full bg-red-500" />
    ) : (
      <span className="inline-block h-2 w-2 rounded-full bg-green-500" />
    )

  return (
    <li className="flex items-start gap-3 py-2">
      <span className="mt-0.5 text-lg leading-none" aria-hidden>
        {icon}
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-neutral-500 uppercase tracking-wide">
            {label}
          </span>
          {statusDot}
          <span className={clsx('text-xs font-medium', statusClass)}>
            {step.status}
          </span>
          {step.cost_usd > 0 && (
            <span className="ml-auto text-xs text-neutral-400">
              ${step.cost_usd.toFixed(5)}
            </span>
          )}
        </div>
        <p className="mt-0.5 text-sm text-neutral-700 break-words">
          {step.description}
        </p>
      </div>
    </li>
  )
}

interface TaskLogProps {
  steps: TaskStep[]
  status: string
}

export function TaskLog({ steps, status }: TaskLogProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [steps.length])

  if (steps.length === 0) {
    return (
      <div className="flex min-h-[120px] items-center justify-center rounded-md border border-dashed border-neutral-200 text-sm text-neutral-400">
        {status === 'running'
          ? 'Waiting for the first step...'
          : 'No steps recorded.'}
      </div>
    )
  }

  return (
    <div className="max-h-[480px] overflow-y-auto rounded-md border border-neutral-200 bg-neutral-50 px-4">
      <ul className="divide-y divide-neutral-100">
        {steps.map((step) => (
          <StepRow key={step.id} step={step} />
        ))}
      </ul>
      <div ref={bottomRef} />
    </div>
  )
}
