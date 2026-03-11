import { type HTMLAttributes } from 'react'
import { clsx } from 'clsx'

interface ProgressProps extends HTMLAttributes<HTMLDivElement> {
  value: number  // 0-100
  max?: number
}

export function Progress({ value, max = 100, className, ...props }: ProgressProps) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100))

  return (
    <div
      role="progressbar"
      aria-valuenow={value}
      aria-valuemin={0}
      aria-valuemax={max}
      className={clsx(
        'relative h-2 w-full overflow-hidden rounded-full bg-neutral-200',
        className
      )}
      {...props}
    >
      <div
        className="h-full rounded-full bg-neutral-900 transition-all duration-300"
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}
