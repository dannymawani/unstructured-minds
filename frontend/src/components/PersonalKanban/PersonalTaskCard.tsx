import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { FileText, GripVertical } from 'lucide-react'
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
}

interface PersonalTaskCardProps {
  task: Task
  onFileSelect?: (path: string) => void
}

const priorityConfig: Record<number, { label: string; className: string }> = {
  1: { label: 'High', className: 'bg-red-500/20 text-red-400 border-red-500/30' },
  2: { label: 'Med', className: 'bg-amber-500/20 text-amber-400 border-amber-500/30' },
  3: { label: 'Low', className: 'bg-zinc-500/20 text-zinc-400 border-zinc-500/30' },
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

export function PersonalTaskCard({ task, onFileSelect }: PersonalTaskCardProps) {
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
    ? categoryColors[task.category.toLowerCase()] || 'bg-zinc-500/20 text-zinc-400'
    : null

  const handleClick = () => {
    if (task.source_file && onFileSelect) {
      onFileSelect(task.source_file)
    }
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      className={cn(
        'bg-zinc-900 border border-zinc-700 rounded-lg p-3 flex gap-2',
        'hover:border-zinc-500 transition-colors text-zinc-100',
        isDragging && 'opacity-50 shadow-lg ring-2 ring-primary/50',
      )}
    >
      {/* Drag handle */}
      <div
        {...listeners}
        className="flex items-start pt-0.5 cursor-grab active:cursor-grabbing text-zinc-600 hover:text-zinc-400 touch-none"
      >
        <GripVertical className="w-4 h-4 flex-shrink-0" />
      </div>

      {/* Clickable content */}
      <div
        className={cn('flex-1 min-w-0', task.source_file && onFileSelect && 'cursor-pointer')}
        onClick={handleClick}
      >
        <p className="text-sm leading-tight mb-2 text-zinc-100">
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
        </div>

        <div className="flex items-center justify-between text-xs text-zinc-500">
          <span>{task.date}</span>
          {task.source_file && (
            <span className="flex items-center gap-1 text-zinc-400">
              <FileText className="w-3 h-3" />
              <span className="max-w-[120px] truncate">
                {getFilename(task.source_file)}
              </span>
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
