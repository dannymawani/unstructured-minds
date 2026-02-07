import { Clock } from 'lucide-react'
import type { KanbanTask } from './KanbanBoard'

interface KanbanCardProps {
  task: KanbanTask
  onClick: () => void
}

const priorityColors: Record<string, string> = {
  'Critical': 'bg-red-500/20 text-red-400 border-red-500/30',
  'High': 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  'high': 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  'Medium': 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  'medium': 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  'Low': 'bg-zinc-500/20 text-zinc-400 border-zinc-500/30',
  'low': 'bg-zinc-500/20 text-zinc-400 border-zinc-500/30',
}

const phaseColors: Record<string, string> = {
  '0': 'bg-purple-500/20 text-purple-400',
  '1': 'bg-blue-500/20 text-blue-400',
  '2': 'bg-cyan-500/20 text-cyan-400',
  '3': 'bg-green-500/20 text-green-400',
  '4': 'bg-yellow-500/20 text-yellow-400',
  '5': 'bg-orange-500/20 text-orange-400',
}

function getPhaseNumber(phase: string | null): string | null {
  if (!phase) return null
  const match = phase.match(/^(\d+)/)
  return match ? match[1] : null
}

/**
 * Try to parse a deadline string into a Date.
 * Returns null if the string isn't a recognizable date.
 */
function parseDeadlineDate(deadline: string): Date | null {
  // Try ISO format first (YYYY-MM-DD)
  const isoMatch = deadline.match(/\d{4}-\d{2}-\d{2}/)
  if (isoMatch) {
    const d = new Date(isoMatch[0] + 'T23:59:59')
    return isNaN(d.getTime()) ? null : d
  }
  // Try natural date parsing (e.g. "Feb 14", "February 14 2026")
  const d = new Date(deadline)
  return isNaN(d.getTime()) ? null : d
}

function getDeadlineUrgency(deadline: string | null): 'overdue' | 'urgent' | 'soon' | 'normal' | null {
  if (!deadline) return null
  const parsed = parseDeadlineDate(deadline)
  if (!parsed) return 'normal' // Can't parse — just show it plainly
  const now = new Date()
  now.setHours(0, 0, 0, 0)
  const diffMs = parsed.getTime() - now.getTime()
  const diffDays = diffMs / (1000 * 60 * 60 * 24)
  if (diffDays < 0) return 'overdue'
  if (diffDays <= 1) return 'urgent'
  if (diffDays <= 3) return 'soon'
  return 'normal'
}

const urgencyStyles: Record<string, string> = {
  overdue: 'text-red-400',
  urgent: 'text-red-400',
  soon: 'text-amber-400',
  normal: 'text-zinc-400',
}

export function KanbanCard({ task, onClick }: KanbanCardProps) {
  const priorityClass = task.priority ? priorityColors[task.priority] || priorityColors['Medium'] : ''
  const phaseNum = getPhaseNumber(task.phase)
  const phaseClass = phaseNum ? phaseColors[phaseNum] || '' : 'bg-zinc-500/20 text-zinc-400'
  const deadlineUrgency = getDeadlineUrgency(task.deadline)

  return (
    <div
      onClick={onClick}
      className="bg-zinc-900 border border-zinc-700 rounded-lg p-3 cursor-pointer hover:border-zinc-500 transition-colors text-zinc-100"
    >
      <h4 className="font-medium text-sm leading-tight mb-2 text-zinc-100">{task.title}</h4>

      {task.description && (
        <p className="text-xs text-zinc-400 line-clamp-2 mb-2">
          {task.description}
        </p>
      )}

      {task.deadline && (
        <div className={`flex items-center gap-1 text-xs mb-2 ${urgencyStyles[deadlineUrgency || 'normal']}`}>
          <Clock className="w-3 h-3" />
          <span>{task.deadline}</span>
          {deadlineUrgency === 'overdue' && <span className="font-semibold">(overdue)</span>}
          {deadlineUrgency === 'urgent' && <span className="font-semibold">(today)</span>}
        </div>
      )}

      <div className="flex flex-wrap gap-1.5">
        {task.phase && (
          <span className={`text-xs px-2 py-0.5 rounded ${phaseClass}`}>
            {task.phase}
          </span>
        )}
        {task.priority && (
          <span className={`text-xs px-2 py-0.5 rounded border ${priorityClass}`}>
            {task.priority}
          </span>
        )}
      </div>
    </div>
  )
}
