import { useEffect, useCallback } from 'react'
import { X, CheckCircle, Clock, PlayCircle, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import type { KanbanTask } from './KanbanBoard'

interface TaskModalProps {
  task: KanbanTask
  onClose: () => void
  onMove: (taskId: string, newStatus: string) => void
  onDelete?: (taskId: string) => void
}

export function TaskModal({ task, onClose, onMove, onDelete }: TaskModalProps) {
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose()
    }
  }, [onClose])

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  const statusButtons = [
    { status: 'not_started', label: 'Not Started', icon: Clock, color: 'text-zinc-400' },
    { status: 'in_progress', label: 'In Progress', icon: PlayCircle, color: 'text-blue-400' },
    { status: 'done', label: 'Done', icon: CheckCircle, color: 'text-green-400' },
  ]

  // Parse markdown content for better display
  const sections = parseMarkdownSections(task.content || '')

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div
        className="bg-zinc-900 border border-zinc-700 rounded-xl w-full max-w-2xl max-h-[85vh] overflow-hidden flex flex-col text-zinc-100"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between p-4 border-b border-zinc-700">
          <div className="flex-1 pr-4">
            <h2 className="text-lg font-semibold text-zinc-100">{task.title}</h2>
            <div className="flex items-center gap-2 mt-2 flex-wrap">
              {task.phase && (
                <span className="text-xs bg-blue-500/20 text-blue-400 px-2 py-1 rounded">
                  {task.phase}
                </span>
              )}
              {task.priority && (
                <span className="text-xs bg-orange-500/20 text-orange-400 px-2 py-1 rounded">
                  {task.priority}
                </span>
              )}
              {task.branch && (
                <span className="text-xs bg-zinc-700 text-zinc-300 px-2 py-1 rounded">
                  {task.branch}
                </span>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-zinc-800 rounded transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Move buttons */}
        <div className="flex items-center gap-2 p-4 border-b border-zinc-700 bg-zinc-800/50">
          <span className="text-sm text-zinc-400 mr-2">Move to:</span>
          {statusButtons.map(({ status, label, icon: Icon, color }) => (
            <Button
              key={status}
              variant={task.status === status ? 'secondary' : 'outline'}
              size="sm"
              onClick={() => onMove(task.id, status)}
              disabled={task.status === status}
              className="gap-1.5"
            >
              <Icon className={`w-4 h-4 ${color}`} />
              {label}
            </Button>
          ))}
          {onDelete && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                if (confirm('Delete this task?')) onDelete(task.id)
              }}
              className="gap-1.5 ml-auto text-red-400 hover:text-red-300 hover:bg-red-500/10"
            >
              <Trash2 className="w-4 h-4" />
              Delete
            </Button>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {sections.map((section, index) => (
            <div key={index} className="mb-4">
              {section.heading && (
                <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wide mb-2">
                  {section.heading}
                </h3>
              )}
              <div className="prose prose-sm prose-invert max-w-none">
                <MarkdownContent content={section.content} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

interface Section {
  heading: string | null
  content: string
}

function parseMarkdownSections(markdown: string): Section[] {
  const lines = markdown.split('\n')
  const sections: Section[] = []
  let currentSection: Section = { heading: null, content: '' }

  for (const line of lines) {
    if (line.startsWith('## ')) {
      if (currentSection.content.trim()) {
        sections.push(currentSection)
      }
      currentSection = {
        heading: line.replace('## ', ''),
        content: '',
      }
    } else if (!line.startsWith('# ')) {
      currentSection.content += line + '\n'
    }
  }

  if (currentSection.content.trim()) {
    sections.push(currentSection)
  }

  return sections.filter(s => s.content.trim())
}

function MarkdownContent({ content }: { content: string }) {
  // Simple markdown rendering
  const lines = content.trim().split('\n')

  return (
    <div className="space-y-2">
      {lines.map((line, i) => {
        // Check for task items
        if (line.match(/^- \[[ x]\]/)) {
          const isChecked = line.includes('[x]')
          const text = line.replace(/^- \[[ x]\]\s*/, '')
          return (
            <div key={i} className="flex items-start gap-2">
              <span className={isChecked ? 'text-green-400' : 'text-zinc-500'}>
                {isChecked ? '✓' : '○'}
              </span>
              <span className={isChecked ? 'text-zinc-500 line-through' : 'text-zinc-200'}>
                {text}
              </span>
            </div>
          )
        }

        // Check for list items
        if (line.match(/^[-*]\s/)) {
          return (
            <div key={i} className="flex items-start gap-2 pl-2">
              <span className="text-zinc-500">•</span>
              <span className="text-zinc-200">{line.replace(/^[-*]\s/, '')}</span>
            </div>
          )
        }

        // Check for code blocks
        if (line.startsWith('```')) {
          return null // Skip code fence markers
        }

        // Check for inline code
        if (line.includes('`')) {
          const parts = line.split(/(`[^`]+`)/)
          return (
            <p key={i} className="text-zinc-200">
              {parts.map((part, j) => {
                if (part.startsWith('`') && part.endsWith('`')) {
                  return (
                    <code key={j} className="bg-zinc-800 text-zinc-300 px-1.5 py-0.5 rounded text-sm">
                      {part.slice(1, -1)}
                    </code>
                  )
                }
                return <span key={j}>{part}</span>
              })}
            </p>
          )
        }

        // Bold text
        if (line.includes('**')) {
          const parts = line.split(/(\*\*[^*]+\*\*)/)
          return (
            <p key={i} className="text-zinc-200">
              {parts.map((part, j) => {
                if (part.startsWith('**') && part.endsWith('**')) {
                  return <strong key={j} className="text-zinc-100">{part.slice(2, -2)}</strong>
                }
                return <span key={j}>{part}</span>
              })}
            </p>
          )
        }

        // Empty lines
        if (!line.trim()) {
          return <div key={i} className="h-2" />
        }

        // Regular paragraph
        return <p key={i} className="text-zinc-200">{line}</p>
      })}
    </div>
  )
}
