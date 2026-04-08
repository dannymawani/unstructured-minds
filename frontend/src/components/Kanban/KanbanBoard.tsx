import { useState, useEffect, useCallback } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { KanbanColumn } from './KanbanColumn'
import { TaskModal } from './TaskModal'

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
  completed_at: string | null
}

interface Column {
  name: string
  status: string
  tasks: KanbanTask[]
}

interface KanbanBoardProps {
  apiUrl: string
}

export function KanbanBoard({ apiUrl }: KanbanBoardProps) {
  const [columns, setColumns] = useState<Column[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedTask, setSelectedTask] = useState<KanbanTask | null>(null)
  const [mobileColumnIndex, setMobileColumnIndex] = useState(0)

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

  const handleTaskClick = (task: KanbanTask) => {
    setSelectedTask(task)
  }

  const handleCloseModal = () => {
    setSelectedTask(null)
  }

  const handleMoveTask = async (taskId: string, newStatus: string) => {
    try {
      const response = await fetch(`${apiUrl}/kanban/task/${taskId}/move?new_status=${newStatus}`, {
        method: 'POST',
      })
      if (!response.ok) throw new Error('Failed to move task')
      await fetchBoard()
      setSelectedTask(null)
    } catch (err) {
      console.error('Error moving task:', err)
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
    <div className="h-full flex flex-col">
      <div className="px-4 sm:px-6 py-3 sm:py-4 border-b border-border">
        <h2 className="text-lg sm:text-xl font-semibold text-foreground">Implementation Kanban</h2>
        <p className="text-xs sm:text-sm text-muted-foreground mt-1">
          {columns.reduce((sum, col) => sum + col.tasks.length, 0)} tasks total
        </p>
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
              tasks={column.tasks}
              onTaskClick={handleTaskClick}
            />
          ))}
        </div>
      </div>

      {selectedTask && (
        <TaskModal
          task={selectedTask}
          onClose={handleCloseModal}
          onMove={handleMoveTask}
        />
      )}
    </div>
  )
}
