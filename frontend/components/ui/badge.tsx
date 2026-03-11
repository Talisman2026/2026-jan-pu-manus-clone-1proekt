import { type HTMLAttributes } from 'react'
import { clsx } from 'clsx'
import type { TaskStatus } from '@/lib/types'

type BadgeVariant = 'default' | 'success' | 'warning' | 'danger' | 'info' | 'neutral'

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant
}

const variantClasses: Record<BadgeVariant, string> = {
  default: 'bg-neutral-100 text-neutral-800',
  success: 'bg-green-100 text-green-800',
  warning: 'bg-yellow-100 text-yellow-800',
  danger: 'bg-red-100 text-red-800',
  info: 'bg-blue-100 text-blue-800',
  neutral: 'bg-neutral-100 text-neutral-600',
}

export function Badge({
  variant = 'default',
  className,
  ...props
}: BadgeProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        variantClasses[variant],
        className
      )}
      {...props}
    />
  )
}

export function StatusBadge({ status }: { status: TaskStatus }) {
  const config: Record<TaskStatus, { label: string; variant: BadgeVariant }> = {
    created: { label: 'Created', variant: 'neutral' },
    estimating: { label: 'Estimating...', variant: 'warning' },
    estimated: { label: 'Estimated', variant: 'info' },
    running: { label: 'Running', variant: 'info' },
    paused: { label: 'Paused', variant: 'warning' },
    completed: { label: 'Completed', variant: 'success' },
    failed: { label: 'Failed', variant: 'danger' },
    budget_warning: { label: 'Budget Warning', variant: 'warning' },
  }

  const { label, variant } = config[status] ?? { label: status, variant: 'neutral' as BadgeVariant }

  return <Badge variant={variant}>{label}</Badge>
}
