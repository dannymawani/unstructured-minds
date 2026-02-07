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
import { Plus, Calendar, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { PersonalTaskCard, type Task } from './PersonalTaskCard'

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
  { id: 'cancelled', label: 'Cancelled', borderColor: 'border-t-zinc-500' },
]

interface NewTaskForm {
  description: string
  category: string
  priority: string
}

const INITIAL_FORM: NewTaskForm = {
  description: '',
  category: '',
  priority: '',
}

function DroppableColumn({
  column,
  tasks,
  onFileSelect,
  children,
}: {
  column: ColumnDef
  tasks: Task[]
  onFileSelect?: (path: string) => void
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
                onFileSelect={onFileSelect}
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
  const [showNewForm, setShowNewForm] = useState(false)
  const [newTask, setNewTask] = useState<NewTaskForm>(INITIAL_FORM)
  const [submitting, setSubmitting] = useState(false)

  // Date filters
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 5 },
    })
  )

  const fetchTasks = useCallback(async () => {
    try {
      setLoading(true)
      const params = new URLSearchParams()
      if (dateFrom) params.set('date_from', dateFrom)
      if (dateTo) params.set('date_to', dateTo)
      const qs = params.toString()
      const url = `${apiUrl}/tasks${qs ? `?${qs}` : ''}`

      const response = await fetch(url)
      if (!response.ok) throw new Error('Failed to fetch tasks')
      const data: TasksResponse = await response.json()
      setTasks(data.tasks)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }, [apiUrl, dateFrom, dateTo])

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
            <h2 className="text-lg sm:text-xl font-semibold text-foreground">
              Personal Tasks
            </h2>
            <p className="text-xs sm:text-sm text-muted-foreground mt-0.5">
              {tasks.length} task{tasks.length !== 1 ? 's' : ''} total
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowNewForm((prev) => !prev)}
          >
            <Plus className="w-4 h-4 mr-1" />
            New Task
          </Button>
        </div>

        {/* Date filters */}
        <div className="flex flex-wrap items-center gap-3 mt-2">
          <div className="flex items-center gap-1.5">
            <Calendar className="w-4 h-4 text-muted-foreground" />
            <label htmlFor="date-from" className="text-xs text-muted-foreground">
              From
            </label>
            <input
              id="date-from"
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="text-xs bg-muted border border-border rounded px-2 py-1 text-foreground"
            />
          </div>
          <div className="flex items-center gap-1.5">
            <label htmlFor="date-to" className="text-xs text-muted-foreground">
              To
            </label>
            <input
              id="date-to"
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="text-xs bg-muted border border-border rounded px-2 py-1 text-foreground"
            />
          </div>
          {(dateFrom || dateTo) && (
            <Button
              variant="ghost"
              size="sm"
              className="text-xs h-7"
              onClick={() => {
                setDateFrom('')
                setDateTo('')
              }}
            >
              Clear
            </Button>
          )}
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
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Category (optional)"
                value={newTask.category}
                onChange={(e) =>
                  setNewTask((prev) => ({ ...prev, category: e.target.value }))
                }
                className="flex-1 bg-background border border-border rounded px-3 py-1.5 text-sm text-foreground placeholder:text-muted-foreground"
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
                onFileSelect={onFileSelect}
              />
            ))}
          </div>
        </div>

        <DragOverlay>
          {activeTask ? (
            <div className="w-72 sm:w-80 opacity-90">
              <PersonalTaskCard task={activeTask} onFileSelect={onFileSelect} />
            </div>
          ) : null}
        </DragOverlay>
      </DndContext>
    </div>
  )
}
