import { useState, useRef, useEffect, useCallback } from 'react'
import { X, FileText, ArrowRight, Pencil, Check, Clock, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { Task } from './PersonalTaskCard'

interface PersonalTaskModalProps {
  task: Task
  apiUrl: string
  onClose: () => void
  onMove: (taskId: string, newStatus: string) => void
  onOpenNote?: (path: string) => void
  onTaskUpdated?: (updated: Task) => void
  onTaskDeleted?: (taskId: string) => void
}

const statusButtons = [
  { status: 'backlog', label: 'Backlog', color: 'text-blue-400' },
  { status: 'in_progress', label: 'In Progress', color: 'text-amber-400' },
  { status: 'done', label: 'Done', color: 'text-green-400' },
  { status: 'cancelled', label: 'Cancelled', color: 'text-muted-foreground' },
]

const priorityConfig: Record<number, { label: string; className: string }> = {
  1: { label: 'High', className: 'bg-red-500/20 text-red-400 border-red-500/30' },
  2: { label: 'Medium', className: 'bg-amber-500/20 text-amber-400 border-amber-500/30' },
  3: { label: 'Low', className: 'bg-muted text-muted-foreground border-border' },
}

const categoryColors: Record<string, string> = {
  work: 'bg-blue-500/20 text-blue-400',
  personal: 'bg-purple-500/20 text-purple-400',
  health: 'bg-green-500/20 text-green-400',
  finance: 'bg-yellow-500/20 text-yellow-400',
  learning: 'bg-cyan-500/20 text-cyan-400',
}

export function PersonalTaskModal({
  task,
  apiUrl,
  onClose,
  onMove,
  onOpenNote,
  onTaskUpdated,
  onTaskDeleted,
}: PersonalTaskModalProps) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(task.description)
  const [categoryDraft, setCategoryDraft] = useState(task.category || '')
  const [saving, setSaving] = useState(false)
  const [confirmingDelete, setConfirmingDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !editing) onClose()
    },
    [onClose, editing]
  )

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  useEffect(() => {
    if (editing) inputRef.current?.focus()
  }, [editing])

  const saveDescription = async () => {
    const trimmed = draft.trim()
    if (!trimmed || trimmed === task.description) {
      setEditing(false)
      setDraft(task.description)
      return
    }
    setSaving(true)
    try {
      const res = await fetch(`${apiUrl}/tasks/${task.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description: trimmed }),
      })
      if (res.ok) {
        const updated: Task = await res.json()
        onTaskUpdated?.(updated)
      }
    } catch (err) {
      console.error('Failed to update description:', err)
    } finally {
      setSaving(false)
      setEditing(false)
    }
  }

  const priority = task.priority != null ? priorityConfig[task.priority] : null
  const categoryClass = task.category
    ? categoryColors[task.category.toLowerCase()] || 'bg-muted text-muted-foreground'
    : null

  const effectiveStatus = task.status || 'backlog'

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div
        className="bg-popover border border-border rounded-lg w-full max-w-lg overflow-hidden flex flex-col text-foreground"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between p-4 border-b border-border">
          <div className="flex-1 pr-4">
            {editing ? (
              <div className="flex gap-2 items-start">
                <textarea
                  ref={inputRef}
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      saveDescription()
                    }
                    if (e.key === 'Escape') {
                      setEditing(false)
                      setDraft(task.description)
                    }
                  }}
                  rows={2}
                  className="flex-1 bg-muted border border-input rounded px-2 py-1 text-sm text-foreground resize-none focus:outline-none focus:ring-1 focus:ring-ring"
                />
                <button
                  onClick={saveDescription}
                  disabled={saving}
                  className="p-1 hover:bg-muted rounded text-teal-400"
                >
                  <Check className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <div className="group flex items-start gap-2">
                <p className="text-base font-semibold text-foreground leading-snug flex-1">
                  {task.description}
                </p>
                <button
                  onClick={() => setEditing(true)}
                  className="p-1 hover:bg-muted rounded text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity"
                  title="Edit description"
                >
                  <Pencil className="w-3.5 h-3.5" />
                </button>
              </div>
            )}
            <div className="flex items-center gap-2 mt-2 flex-wrap">
              {task.category && categoryClass && (
                <span className={cn('text-xs px-2 py-0.5 rounded', categoryClass)}>
                  {task.category}
                </span>
              )}
              {priority && (
                <span className={cn('text-xs px-2 py-0.5 rounded border', priority.className)}>
                  {priority.label}
                </span>
              )}
              <span className="text-xs bg-secondary text-muted-foreground px-2 py-0.5 rounded">
                {effectiveStatus.replace('_', ' ')}
              </span>
              {task.deadline && (
                <span className="flex items-center gap-1 text-xs bg-amber-500/20 text-amber-400 px-2 py-0.5 rounded">
                  <Clock className="w-3 h-3" />
                  {new Date(task.deadline + 'T00:00:00').toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
                </span>
              )}
              <span className="text-xs text-muted-foreground">{task.date}</span>
            </div>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-muted rounded transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Deadline + Category */}
        <div className="flex items-center gap-4 px-4 py-3 border-b border-border flex-wrap">
          <div className="flex items-center gap-3">
            <span className="text-sm text-muted-foreground">Deadline:</span>
            <input
              type="date"
              value={task.deadline || ''}
              onChange={async (e) => {
                const val = e.target.value || null
                try {
                  const res = await fetch(`${apiUrl}/tasks/${task.id}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ deadline: val }),
                  })
                  if (res.ok) {
                    const updated: Task = await res.json()
                    onTaskUpdated?.(updated)
                  }
                } catch (err) {
                  console.error('Failed to update deadline:', err)
                }
              }}
              className="bg-muted border border-border rounded px-2 py-1 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
            />
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-muted-foreground">Category:</span>
            <input
              type="text"
              value={categoryDraft}
              placeholder="e.g. work, personal"
              onChange={(e) => setCategoryDraft(e.target.value)}
              onBlur={async () => {
                const val = categoryDraft.trim() || null
                if (val === (task.category || null)) return
                try {
                  const res = await fetch(`${apiUrl}/tasks/${task.id}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ category: val }),
                  })
                  if (res.ok) {
                    const updated: Task = await res.json()
                    onTaskUpdated?.(updated)
                  }
                } catch (err) {
                  console.error('Failed to update category:', err)
                }
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter') (e.target as HTMLInputElement).blur()
              }}
              className="bg-muted border border-border rounded px-2 py-1 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring w-36"
            />
          </div>
        </div>

        {/* Move-to buttons */}
        <div className="flex items-center gap-2 p-4 border-b border-border bg-muted flex-wrap">
          <span className="text-sm text-muted-foreground mr-1">Move to:</span>
          {statusButtons.map(({ status, label, color }) => (
            <Button
              key={status}
              variant={effectiveStatus === status ? 'secondary' : 'outline'}
              size="sm"
              onClick={() => onMove(task.id, status)}
              disabled={effectiveStatus === status}
              className="gap-1.5"
            >
              <ArrowRight className={cn('w-3.5 h-3.5', color)} />
              {label}
            </Button>
          ))}
        </div>

        {/* Source file link + Delete */}
        <div className="p-4 flex items-center justify-between">
          {onOpenNote ? (
            <button
              onClick={() => {
                let notePath: string
                if (task.source_file && task.source_file.endsWith('.md')) {
                  notePath = task.source_file
                } else {
                  const [year, month] = task.date.split('-')
                  notePath = `Daily-Notes/${year}-${month}/${task.date}.md`
                }
                onOpenNote(notePath)
              }}
              className="flex items-center gap-2 text-sm text-teal-400 hover:text-teal-300 transition-colors"
            >
              <FileText className="w-4 h-4" />
              Open in Daily Note
            </button>
          ) : (
            <div />
          )}

          {onTaskDeleted && !confirmingDelete && (
            <button
              onClick={() => setConfirmingDelete(true)}
              className="flex items-center gap-1.5 text-sm text-red-400 hover:text-red-300 transition-colors"
            >
              <Trash2 className="w-4 h-4" />
              Delete
            </button>
          )}

          {confirmingDelete && (
            <div className="flex items-center gap-2 text-sm">
              <span className="text-muted-foreground">Are you sure?</span>
              <button
                onClick={async () => {
                  setDeleting(true)
                  try {
                    const res = await fetch(`${apiUrl}/tasks/${task.id}`, {
                      method: 'DELETE',
                    })
                    if (res.ok || res.status === 204) {
                      onTaskDeleted(task.id)
                      onClose()
                    }
                  } catch (err) {
                    console.error('Failed to delete task:', err)
                  } finally {
                    setDeleting(false)
                    setConfirmingDelete(false)
                  }
                }}
                disabled={deleting}
                className="px-2 py-1 rounded bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors"
              >
                {deleting ? 'Deleting...' : 'Confirm'}
              </button>
              <button
                onClick={() => setConfirmingDelete(false)}
                className="px-2 py-1 rounded bg-muted text-muted-foreground hover:bg-muted/80 transition-colors"
              >
                Cancel
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
