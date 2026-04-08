import { useState, useEffect, useCallback } from 'react'
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core'
import type { DragStartEvent, DragEndEvent } from '@dnd-kit/core'
import { ChevronLeft, ChevronRight, Plus, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { KanbanColumn } from './KanbanColumn'
import { KanbanCard } from './KanbanCard'
import { TaskModal } from './TaskModal'
import { PersonalKanban } from '../PersonalKanban/PersonalKanban'
import { cn } from '@/lib/utils'

export interface KanbanTask {
  id: string
  title: string
  phase: string | null
  priority: string | null
  status: string
  branch: string | null
  depends_on: string | null
  description: string | null
  content: string | null
  deadline: string | null
  completed_at: string | null
}

interface Column {
  name: string
  status: string
  tasks: KanbanTask[]
}

interface KanbanBoardProps {
  apiUrl: string
  onFileSelect?: (path: string) => void
}

type KanbanTab = 'personal' | 'implementation'

const COLUMN_STATUSES = ['not_started', 'in_progress', 'done']

export function KanbanBoard({ apiUrl, onFileSelect }: KanbanBoardProps) {
  return <PersonalKanban apiUrl={apiUrl} onFileSelect={onFileSelect} />
}

function ImplementationKanban({ apiUrl }: { apiUrl: string }) {
  const [columns, setColumns] = useState<Column[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedTask, setSelectedTask] = useState<KanbanTask | null>(null)
  const [mobileColumnIndex, setMobileColumnIndex] = useState(0)
  const [showNewForm, setShowNewForm] = useState(false)
  const [newTitle, setNewTitle] = useState('')
  const [newDescription, setNewDescription] = useState('')
  const [newPriority, setNewPriority] = useState('')
  const [newDeadline, setNewDeadline] = useState('')
  const [creating, setCreating] = useState(false)
  const [activeTask, setActiveTask] = useState<KanbanTask | null>(null)

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 5 },
    })
  )

  const fetchBoard = useCallback(async () => {
    try {
      setLoading(true)
      const response = await fetch(`${apiUrl}/kanban/board`)
      if (!response.ok) throw new Error('Failed to fetch board')
      const data = await response.json()
      setColumns(data.columns)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }, [apiUrl])

  useEffect(() => {
    fetchBoard()
  }, [fetchBoard])

  // Find all tasks flattened
  const allTasks = columns.flatMap((c) => c.tasks)

  const handleTaskClick = (task: KanbanTask) => {
    setSelectedTask(task)
  }

  const handleCloseModal = () => {
    setSelectedTask(null)
  }

  const handleMoveTask = async (taskId: string, newStatus: string) => {
    // Optimistic update
    setColumns((prev) =>
      prev.map((col) => ({
        ...col,
        tasks:
          col.status === newStatus
            ? [...col.tasks, ...prev.flatMap((c) => c.tasks).filter((t) => t.id === taskId).map((t) => ({ ...t, status: newStatus }))]
            : col.tasks.filter((t) => t.id !== taskId),
      }))
    )
    setSelectedTask(null)

    try {
      const response = await fetch(`${apiUrl}/kanban/task/${taskId}/move?new_status=${newStatus}`, {
        method: 'POST',
      })
      if (!response.ok) throw new Error('Failed to move task')
      await fetchBoard()
    } catch (err) {
      console.error('Error moving task:', err)
      await fetchBoard() // rollback
    }
  }

  const handleDragStart = useCallback(
    (event: DragStartEvent) => {
      const task = allTasks.find((t) => t.id === event.active.id)
      if (task) setActiveTask(task)
    },
    [allTasks]
  )

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      setActiveTask(null)
      const { active, over } = event
      if (!over) return

      const taskId = active.id as string
      const targetStatus = over.id as string

      // Only process if dropped on a valid column
      if (!COLUMN_STATUSES.includes(targetStatus)) return

      // Find source status
      const sourceCol = columns.find((c) => c.tasks.some((t) => t.id === taskId))
      if (!sourceCol || sourceCol.status === targetStatus) return

      handleMoveTask(taskId, targetStatus)
    },
    [columns, handleMoveTask]
  )

  const handleDragCancel = useCallback(() => {
    setActiveTask(null)
  }, [])

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newTitle.trim()) return

    setCreating(true)
    try {
      const response = await fetch(`${apiUrl}/kanban/task`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: newTitle.trim(),
          description: newDescription.trim() || null,
          priority: newPriority || null,
          deadline: newDeadline.trim() || null,
        }),
      })
      if (!response.ok) {
        const err = await response.json().catch(() => ({}))
        throw new Error(err.detail || 'Failed to create task')
      }
      setNewTitle('')
      setNewDescription('')
      setNewPriority('')
      setNewDeadline('')
      setShowNewForm(false)
      await fetchBoard()
    } catch (err) {
      console.error('Error creating task:', err)
      setError(err instanceof Error ? err.message : 'Failed to create task')
    } finally {
      setCreating(false)
    }
  }

  const handleDeleteTask = async (taskId: string) => {
    try {
      const response = await fetch(`${apiUrl}/kanban/task/${taskId}`, {
        method: 'DELETE',
      })
      if (!response.ok) throw new Error('Failed to delete task')
      await fetchBoard()
      setSelectedTask(null)
    } catch (err) {
      console.error('Error deleting task:', err)
    }
  }

  const goToPrevColumn = () => {
    setMobileColumnIndex((prev) => Math.max(0, prev - 1))
  }

  const goToNextColumn = () => {
    setMobileColumnIndex((prev) => Math.min(columns.length - 1, prev + 1))
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-muted-foreground">Loading kanban board...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-red-500">Error: {error}</div>
      </div>
    )
  }

  return (
    <DndContext
      sensors={sensors}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      onDragCancel={handleDragCancel}
    >
      <div className="h-full flex flex-col">
        <div className="px-4 sm:px-6 py-3 sm:py-4 border-b border-border">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg sm:text-xl font-semibold text-foreground">Implementation Kanban</h2>
              <p className="text-xs sm:text-sm text-muted-foreground mt-1">
                {columns.reduce((sum, col) => sum + col.tasks.length, 0)} tasks total
              </p>
            </div>
            <Button
              size="sm"
              onClick={() => setShowNewForm((prev) => !prev)}
              className="gap-1"
            >
              {showNewForm ? <X className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
              {showNewForm ? 'Cancel' : 'New Task'}
            </Button>
          </div>

          {showNewForm && (
            <form onSubmit={handleCreateTask} className="mt-3 flex flex-col gap-2">
              <input
                type="text"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                placeholder="Task title..."
                className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                autoFocus
              />
              <input
                type="text"
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
                placeholder="Description (optional)"
                className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
              <div className="flex gap-2 items-center flex-wrap">
                <select
                  value={newPriority}
                  onChange={(e) => setNewPriority(e.target.value)}
                  className="rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  <option value="">Priority</option>
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
                <input
                  type="date"
                  value={newDeadline}
                  onChange={(e) => setNewDeadline(e.target.value)}
                  className="flex-1 min-w-[150px] rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                />
                <Button type="submit" size="sm" disabled={!newTitle.trim() || creating}>
                  {creating ? 'Creating...' : 'Add Task'}
                </Button>
              </div>
            </form>
          )}
        </div>

        {/* Mobile column navigation */}
        <div className="sm:hidden flex items-center justify-between px-4 py-2 border-b border-border bg-muted/50">
          <Button
            variant="ghost"
            size="sm"
            onClick={goToPrevColumn}
            disabled={mobileColumnIndex === 0}
            className="min-w-[44px] min-h-[44px]"
          >
            <ChevronLeft className="w-5 h-5" />
          </Button>
          <div className="flex items-center gap-2">
            {columns.map((_, index) => (
              <button
                key={index}
                onClick={() => setMobileColumnIndex(index)}
                className={`w-2 h-2 rounded-full transition-colors ${
                  index === mobileColumnIndex ? 'bg-primary' : 'bg-muted-foreground/30'
                }`}
                aria-label={`Go to column ${index + 1}`}
              />
            ))}
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={goToNextColumn}
            disabled={mobileColumnIndex === columns.length - 1}
            className="min-w-[44px] min-h-[44px]"
          >
            <ChevronRight className="w-5 h-5" />
          </Button>
        </div>

        {/* Mobile: Single column view */}
        <div className="sm:hidden flex-1 overflow-y-auto p-4">
          {columns[mobileColumnIndex] && (
            <KanbanColumn
              name={columns[mobileColumnIndex].name}
              status={columns[mobileColumnIndex].status}
              tasks={columns[mobileColumnIndex].tasks}
              onTaskClick={handleTaskClick}
              fullWidth
            />
          )}
        </div>

        {/* Desktop: Horizontal scroll view */}
        <div className="hidden sm:block flex-1 overflow-x-auto p-4 sm:p-6">
          <div className="flex gap-4 sm:gap-6 h-full min-w-max">
            {columns.map((column) => (
              <KanbanColumn
                key={column.name}
                name={column.name}
                status={column.status}
                tasks={column.tasks}
                onTaskClick={handleTaskClick}
              />
            ))}
          </div>
        </div>

        {selectedTask && (
          <TaskModal
            task={selectedTask}
            apiUrl={apiUrl}
            onClose={handleCloseModal}
            onMove={handleMoveTask}
            onDelete={handleDeleteTask}
          />
        )}
      </div>

      <DragOverlay>
        {activeTask ? (
          <div className="w-72 sm:w-80">
            <KanbanCard task={activeTask} onClick={() => {}} isDragOverlay />
          </div>
        ) : null}
      </DragOverlay>
    </DndContext>
  )
}
