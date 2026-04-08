import { useState, useEffect, useCallback } from 'react'
import {
  DndContext,
  DragOverlay,
  closestCorners,
  PointerSensor,
  useSensor,
  useSensors,
  useDroppable,
} from '@dnd-kit/core'
import type { DragStartEvent, DragOverEvent, DragEndEvent } from '@dnd-kit/core'
import {
  SortableContext,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { Plus, Loader2, ListTodo, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { PersonalTaskCard, type Task } from './PersonalTaskCard'
import { PersonalTaskModal } from './PersonalTaskModal'

interface PersonalKanbanProps {
  apiUrl: string
  onFileSelect?: (path: string) => void
}

interface TasksResponse {
  tasks: Task[]
  total: number
}

type ColumnId = 'backlog' | 'in_progress' | 'done' | 'cancelled'

interface ColumnDef {
  id: ColumnId
  label: string
  borderColor: string
}

const COLUMNS: ColumnDef[] = [
  { id: 'backlog', label: 'Backlog', borderColor: 'border-t-blue-500' },
  { id: 'in_progress', label: 'In Progress', borderColor: 'border-t-amber-500' },
  { id: 'done', label: 'Done', borderColor: 'border-t-green-500' },
  { id: 'cancelled', label: 'Cancelled', borderColor: 'border-t-muted-foreground' },
]

interface NewTaskForm {
  description: string
  category: string
  priority: string
  deadline: string
}

const INITIAL_FORM: NewTaskForm = {
  description: '',
  category: '',
  priority: '',
  deadline: '',
}

function DroppableColumn({
  column,
  tasks,
  onTaskClick,
  children,
}: {
  column: ColumnDef
  tasks: Task[]
  onTaskClick?: (task: Task) => void
  children?: React.ReactNode
}) {
  const { setNodeRef, isOver } = useDroppable({ id: column.id })

  return (
    <div className="flex flex-col w-72 sm:w-80 flex-shrink-0">
      <div className={cn('bg-card rounded-t-lg p-3 border-t-4', column.borderColor)}>
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium text-foreground">{column.label}</h3>
          <span className="text-sm text-muted-foreground bg-muted px-2 py-0.5 rounded">
            {tasks.length}
          </span>
        </div>
      </div>

      <div
        ref={setNodeRef}
        className={cn(
          'flex-1 bg-card/50 rounded-b-lg p-2 overflow-y-auto max-h-[calc(100vh-320px)]',
          'transition-colors',
          isOver && 'bg-primary/5 ring-1 ring-primary/30'
        )}
      >
        <SortableContext
          items={tasks.map((t) => t.id)}
          strategy={verticalListSortingStrategy}
        >
          <div className="space-y-2">
            {children}
            {tasks.map((task) => (
              <PersonalTaskCard
                key={task.id}
                task={task}
                onTaskClick={onTaskClick}
              />
            ))}
            {tasks.length === 0 && (
              <div className="text-center text-sm text-muted-foreground py-8">
                No tasks
              </div>
            )}
          </div>
        </SortableContext>
      </div>
    </div>
  )
}

export function PersonalKanban({ apiUrl, onFileSelect }: PersonalKanbanProps) {
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTask, setActiveTask] = useState<Task | null>(null)
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const [showNewForm, setShowNewForm] = useState(false)
  const [newTask, setNewTask] = useState<NewTaskForm>(INITIAL_FORM)
  const [submitting, setSubmitting] = useState(false)
  const [clearing, setClearing] = useState(false)

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 5 },
    })
  )

  const fetchTasks = useCallback(async () => {
    try {
      setLoading(true)
      const response = await fetch(`${apiUrl}/tasks`)
      if (!response.ok) throw new Error('Failed to fetch tasks')
      const data: TasksResponse = await response.json()
      setTasks(data.tasks)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }, [apiUrl])

  useEffect(() => {
    fetchTasks()
  }, [fetchTasks])

  const getColumnTasks = useCallback(
    (columnId: ColumnId): Task[] => {
      return tasks.filter((t) => {
        if (columnId === 'backlog') {
          return t.status === 'backlog' || t.status === null
        }
        return t.status === columnId
      })
    },
    [tasks]
  )

  const updateTaskStatus = useCallback(
    async (taskId: string, newStatus: string) => {
      // Optimistic update
      const previousTasks = [...tasks]
      setTasks((prev) =>
        prev.map((t) => (t.id === taskId ? { ...t, status: newStatus } : t))
      )

      try {
        const response = await fetch(`${apiUrl}/tasks/${taskId}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status: newStatus }),
        })
        if (!response.ok) {
          throw new Error('Failed to update task status')
        }
      } catch {
        // Rollback on error
        setTasks(previousTasks)
        setError('Failed to update task. Changes have been reverted.')
        setTimeout(() => setError(null), 3000)
      }
    },
    [apiUrl, tasks]
  )

  const handleDragStart = useCallback(
    (event: DragStartEvent) => {
      const task = tasks.find((t) => t.id === event.active.id)
      if (task) {
        setActiveTask(task)
      }
    },
    [tasks]
  )

  const findColumnForTask = useCallback(
    (taskId: string): ColumnId | null => {
      const task = tasks.find((t) => t.id === taskId)
      if (!task) return null
      if (task.status === null || task.status === 'backlog') return 'backlog'
      return (task.status as ColumnId) || null
    },
    [tasks]
  )

  const handleDragOver = useCallback((_event: DragOverEvent) => {
    // Visual feedback is handled by the isOver state in DroppableColumn
  }, [])

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      setActiveTask(null)

      const { active, over } = event
      if (!over) return

      const activeId = active.id as string
      const overId = over.id as string

      // Determine which column was dropped on
      const isColumnId = COLUMNS.some((c) => c.id === overId)
      const targetColumn = isColumnId
        ? (overId as ColumnId)
        : findColumnForTask(overId)

      if (!targetColumn) return

      const sourceColumn = findColumnForTask(activeId)
      if (sourceColumn === targetColumn) return

      updateTaskStatus(activeId, targetColumn)
    },
    [findColumnForTask, updateTaskStatus]
  )

  const handleDragCancel = useCallback(() => {
    setActiveTask(null)
  }, [])

  const handleSubmitNewTask = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault()
      if (!newTask.description.trim()) return

      setSubmitting(true)
      try {
        const body: Record<string, string | number> = {
          description: newTask.description.trim(),
          status: 'backlog',
        }
        if (newTask.category.trim()) body.category = newTask.category.trim()
        if (newTask.priority) body.priority = Number(newTask.priority)
        if (newTask.deadline) body.deadline = newTask.deadline

        const response = await fetch(`${apiUrl}/tasks`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
        if (!response.ok) throw new Error('Failed to create task')

        setNewTask(INITIAL_FORM)
        setShowNewForm(false)
        await fetchTasks()
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to create task')
      } finally {
        setSubmitting(false)
      }
    },
    [apiUrl, newTask, fetchTasks]
  )

  const handleClearAll = useCallback(async () => {
    if (!confirm('Are you sure you want to delete ALL tasks? This cannot be undone.')) return
    setClearing(true)
    try {
      const response = await fetch(`${apiUrl}/tasks/clear-all`, { method: 'DELETE' })
      if (!response.ok) throw new Error('Failed to clear tasks')
      setTasks([])
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to clear tasks')
    } finally {
      setClearing(false)
    }
  }, [apiUrl])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
        <span className="ml-2 text-muted-foreground">Loading tasks...</span>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="px-4 sm:px-6 py-3 sm:py-4 border-b border-border">
        <div className="flex items-center justify-between mb-2">
          <div>
            <div className="flex items-center gap-2">
              <ListTodo className="w-5 h-5 text-accent" />
              <h2 className="text-lg sm:text-xl font-semibold text-foreground">
                Personal Tasks
              </h2>
            </div>
            <p className="text-xs sm:text-sm text-muted-foreground mt-0.5">
              {tasks.length} task{tasks.length !== 1 ? 's' : ''} total
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowNewForm((prev) => !prev)}
            >
              <Plus className="w-4 h-4 mr-1" />
              New Task
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleClearAll}
              disabled={clearing || tasks.length === 0}
              className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
            >
              {clearing ? <Loader2 className="w-4 h-4 mr-1 animate-spin" /> : <Trash2 className="w-4 h-4 mr-1" />}
              Clear All
            </Button>
          </div>
        </div>

        {/* Inline new task form */}
        {showNewForm && (
          <form
            onSubmit={handleSubmitNewTask}
            className="mt-3 p-3 bg-muted rounded-lg border border-border space-y-2"
          >
            <input
              type="text"
              placeholder="Task description..."
              value={newTask.description}
              onChange={(e) =>
                setNewTask((prev) => ({ ...prev, description: e.target.value }))
              }
              className="w-full bg-background border border-border rounded px-3 py-1.5 text-sm text-foreground placeholder:text-muted-foreground"
              autoFocus
            />
            <div className="flex gap-2 flex-wrap">
              <input
                type="text"
                placeholder="Category (optional)"
                value={newTask.category}
                onChange={(e) =>
                  setNewTask((prev) => ({ ...prev, category: e.target.value }))
                }
                className="flex-1 min-w-[120px] bg-background border border-border rounded px-3 py-1.5 text-sm text-foreground placeholder:text-muted-foreground"
              />
              <select
                value={newTask.priority}
                onChange={(e) =>
                  setNewTask((prev) => ({ ...prev, priority: e.target.value }))
                }
                className="bg-background border border-border rounded px-3 py-1.5 text-sm text-foreground"
              >
                <option value="">Priority</option>
                <option value="1">High</option>
                <option value="2">Medium</option>
                <option value="3">Low</option>
              </select>
              <input
                type="date"
                value={newTask.deadline}
                onChange={(e) =>
                  setNewTask((prev) => ({ ...prev, deadline: e.target.value }))
                }
                className="bg-background border border-border rounded px-3 py-1.5 text-sm text-foreground"
                title="Deadline (optional)"
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => {
                  setShowNewForm(false)
                  setNewTask(INITIAL_FORM)
                }}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                size="sm"
                disabled={!newTask.description.trim() || submitting}
              >
                {submitting && <Loader2 className="w-3 h-3 mr-1 animate-spin" />}
                Add Task
              </Button>
            </div>
          </form>
        )}
      </div>

      {/* Error banner */}
      {error && (
        <div className="px-4 sm:px-6 py-2 bg-red-500/10 border-b border-red-500/20">
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      {/* Kanban columns */}
      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragOver={handleDragOver}
        onDragEnd={handleDragEnd}
        onDragCancel={handleDragCancel}
      >
        <div className="flex-1 overflow-x-auto p-4 sm:p-6">
          <div className="flex gap-4 sm:gap-6 h-full min-w-max">
            {COLUMNS.map((column) => (
              <DroppableColumn
                key={column.id}
                column={column}
                tasks={getColumnTasks(column.id)}
                onTaskClick={(task) => setSelectedTask(task)}
              />
            ))}
          </div>
        </div>

        <DragOverlay>
          {activeTask ? (
            <div className="w-72 sm:w-80 opacity-90">
              <PersonalTaskCard task={activeTask} />
            </div>
          ) : null}
        </DragOverlay>
      </DndContext>

      {selectedTask && (
        <PersonalTaskModal
          task={selectedTask}
          apiUrl={apiUrl}
          onClose={() => setSelectedTask(null)}
          onMove={(taskId, newStatus) => {
            updateTaskStatus(taskId, newStatus)
            setSelectedTask(null)
          }}
          onOpenNote={(path) => {
            setSelectedTask(null)
            onFileSelect?.(path)
          }}
          onTaskUpdated={(updated) => {
            setTasks((prev) => prev.map((t) => (t.id === updated.id ? updated : t)))
            setSelectedTask(updated)
          }}
          onTaskDeleted={(taskId) => {
            setTasks((prev) => prev.filter((t) => t.id !== taskId))
            setSelectedTask(null)
          }}
        />
      )}
    </div>
  )
}
