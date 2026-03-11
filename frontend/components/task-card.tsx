import Link from 'next/link'
import { Card, CardContent } from '@/components/ui/card'
import { StatusBadge } from '@/components/ui/badge'
import type { TaskListItem } from '@/lib/types'

interface TaskCardProps {
  task: TaskListItem
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function truncate(text: string, max = 120): string {
  if (text.length <= max) return text
  return text.slice(0, max).trimEnd() + '…'
}

export function TaskCard({ task }: TaskCardProps) {
  return (
    <Link href={`/task/${task.id}`} className="block group">
      <Card className="transition-shadow group-hover:shadow-md">
        <CardContent className="pt-4 pb-4">
          <div className="flex items-start justify-between gap-3">
            <p className="text-sm text-neutral-800 leading-relaxed flex-1 min-w-0">
              {truncate(task.description)}
            </p>
            <StatusBadge status={task.status} />
          </div>
          <div className="mt-3 flex items-center gap-4 text-xs text-neutral-400">
            <span>{formatDate(task.created_at)}</span>
            {task.cost_actual > 0 && (
              <span className="text-neutral-600">
                ${task.cost_actual.toFixed(4)} spent
              </span>
            )}
            {task.budget_cap !== null && (
              <span>cap ${task.budget_cap.toFixed(2)}</span>
            )}
          </div>
        </CardContent>
      </Card>
    </Link>
  )
}
