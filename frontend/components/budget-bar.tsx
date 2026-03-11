import { clsx } from 'clsx'

interface BudgetBarProps {
  cost_actual: number
  budget_cap: number
}

export function BudgetBar({ cost_actual, budget_cap }: BudgetBarProps) {
  const pct = budget_cap > 0 ? Math.min(100, (cost_actual / budget_cap) * 100) : 0

  const barColor =
    pct >= 80
      ? 'bg-red-500'
      : pct >= 50
        ? 'bg-yellow-400'
        : 'bg-green-500'

  const textColor =
    pct >= 80
      ? 'text-red-600'
      : pct >= 50
        ? 'text-yellow-600'
        : 'text-green-600'

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-sm">
        <span className="text-neutral-500">Budget used</span>
        <span className={clsx('font-medium', textColor)}>
          ${cost_actual.toFixed(4)} / ${budget_cap.toFixed(2)}
          <span className="ml-2 text-neutral-400">({pct.toFixed(0)}%)</span>
        </span>
      </div>
      <div className="relative h-2 w-full overflow-hidden rounded-full bg-neutral-200">
        <div
          className={clsx('h-full rounded-full transition-all duration-500', barColor)}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}
