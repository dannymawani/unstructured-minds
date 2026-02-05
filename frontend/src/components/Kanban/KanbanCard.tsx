import type { KanbanTask } from './KanbanBoard'

interface KanbanCardProps {
  task: KanbanTask
  onClick: () => void
}

const priorityColors: Record<string, string> = {
  'Critical': 'bg-red-500/20 text-red-400 border-red-500/30',
  'High': 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  'Medium': 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  'Low': 'bg-zinc-500/20 text-zinc-400 border-zinc-500/30',
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

export function KanbanCard({ task, onClick }: KanbanCardProps) {
  const priorityClass = task.priority ? priorityColors[task.priority] || priorityColors['Medium'] : ''
  const phaseNum = getPhaseNumber(task.phase)
  const phaseClass = phaseNum ? phaseColors[phaseNum] || '' : 'bg-zinc-500/20 text-zinc-400'

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
