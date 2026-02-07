import { useRef } from 'react'
import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { Clock, FileText } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface Task {
  id: string
  date: string
  description: string
  status: string | null
  completed_at: string | null
  category: string | null
  priority: number | null
  source_file: string | null
  deadline: string | null
}

interface PersonalTaskCardProps {
  task: Task
  onTaskClick?: (task: Task) => void
}

const priorityConfig: Record<number, { label: string; className: string }> = {
  1: { label: 'High', className: 'bg-red-500/20 text-red-400 border-red-500/30' },
  2: { label: 'Med', className: 'bg-amber-500/20 text-amber-400 border-amber-500/30' },
  3: { label: 'Low', className: 'bg-muted text-muted-foreground border-border' },
}

const categoryColors: Record<string, string> = {
  work: 'bg-blue-500/20 text-blue-400',
  personal: 'bg-purple-500/20 text-purple-400',
  health: 'bg-green-500/20 text-green-400',
  finance: 'bg-yellow-500/20 text-yellow-400',
  learning: 'bg-cyan-500/20 text-cyan-400',
}

function getFilename(path: string): string {
  const parts = path.split('/')
  return parts[parts.length - 1] || path
}

export function PersonalTaskCard({ task, onTaskClick }: PersonalTaskCardProps) {
  const mouseStart = useRef<{ x: number; y: number } | null>(null)

  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: task.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  const priority = task.priority != null ? priorityConfig[task.priority] : null
  const categoryClass = task.category
    ? categoryColors[task.category.toLowerCase()] || 'bg-muted text-muted-foreground'
    : null

  // Use mouse events for click detection — completely independent of
  // dnd-kit's pointer event system, so no interference.
  const handleMouseDown = (e: React.MouseEvent) => {
    mouseStart.current = { x: e.clientX, y: e.clientY }
  }

  const handleMouseUp = (e: React.MouseEvent) => {
    if (!mouseStart.current) return
    const dx = e.clientX - mouseStart.current.x
    const dy = e.clientY - mouseStart.current.y
    mouseStart.current = null
    if (Math.abs(dx) < 5 && Math.abs(dy) < 5) {
      onTaskClick?.(task)
    }
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      onMouseDown={handleMouseDown}
      onMouseUp={handleMouseUp}
      className={cn(
        'bg-popover border border-border rounded-lg p-3 cursor-grab',
        'hover:border-muted-foreground transition-colors text-foreground',
        'active:cursor-grabbing',
        isDragging && 'opacity-50 shadow-lg ring-2 ring-primary/50',
      )}
    >
      <p className="text-sm leading-tight mb-2 text-foreground">
        {task.description}
      </p>

      <div className="flex flex-wrap items-center gap-1.5 mb-2">
        {task.category && categoryClass && (
          <span className={cn('text-xs px-2 py-0.5 rounded', categoryClass)}>
            {task.category}
          </span>
        )}
        {priority && (
          <span
            className={cn(
              'text-xs px-2 py-0.5 rounded border',
              priority.className
            )}
          >
            {priority.label}
          </span>
        )}
        {task.deadline && (
          <span className="flex items-center gap-1 text-xs bg-amber-500/20 text-amber-400 px-2 py-0.5 rounded">
            <Clock className="w-3 h-3" />
            {new Date(task.deadline + 'T00:00:00').toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
          </span>
        )}
      </div>

      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>{task.date}</span>
        {task.source_file && (
          <span className="flex items-center gap-1 text-muted-foreground">
            <FileText className="w-3 h-3" />
            <span className="max-w-[120px] truncate">
              {getFilename(task.source_file)}
            </span>
          </span>
        )}
      </div>
    </div>
  )
}
