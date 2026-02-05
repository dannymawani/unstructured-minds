import type { KanbanTask } from './KanbanBoard'
import { KanbanCard } from './KanbanCard'

interface KanbanColumnProps {
  name: string
  tasks: KanbanTask[]
  onTaskClick: (task: KanbanTask) => void
  fullWidth?: boolean
}

const columnColors: Record<string, string> = {
  'Not Started': 'border-t-zinc-500',
  'In Progress': 'border-t-blue-500',
  'Done': 'border-t-green-500',
}

export function KanbanColumn({ name, tasks, onTaskClick, fullWidth = false }: KanbanColumnProps) {
  const borderColor = columnColors[name] || 'border-t-zinc-500'

  return (
    <div className={`flex flex-col ${fullWidth ? 'w-full' : 'w-72 sm:w-80'} flex-shrink-0`}>
      <div className={`bg-card rounded-t-lg p-3 border-t-4 ${borderColor}`}>
        <div className="flex items-center justify-between">
          <h3 className="font-medium text-foreground">{name}</h3>
          <span className="text-sm text-muted-foreground bg-muted px-2 py-0.5 rounded">
            {tasks.length}
          </span>
        </div>
      </div>

      <div className={`flex-1 bg-card/50 rounded-b-lg p-2 overflow-y-auto ${fullWidth ? 'max-h-[calc(100vh-280px)]' : 'max-h-[calc(100vh-240px)]'}`}>
        <div className="space-y-2">
          {tasks.map((task) => (
            <KanbanCard
              key={task.id}
              task={task}
              onClick={() => onTaskClick(task)}
            />
          ))}
          {tasks.length === 0 && (
            <div className="text-center text-sm text-muted-foreground py-8">
              No tasks
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
