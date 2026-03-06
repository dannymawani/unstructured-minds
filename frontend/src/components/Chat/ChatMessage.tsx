import { cn } from '@/lib/utils'
import { User, Bot, Database, ChevronDown, ChevronUp, FileCheck, CalendarPlus } from 'lucide-react'
import { useState } from 'react'

export interface ImageAttachment {
  data: string
  media_type: string
  preview?: string
}

export interface QueryData {
  columns: string[]
  data: Record<string, unknown>[]
  sql?: string
  rowCount: number
}

export interface CreatedNoteInfo {
  date: string
  path: string
  created: boolean
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp?: Date
  queryData?: QueryData
  images?: ImageAttachment[]
  noteUpdated?: boolean
  createdNotes?: CreatedNoteInfo[]
}

function DataTable({ queryData }: { queryData: QueryData }) {
  const [showSql, setShowSql] = useState(false)
  const { columns, data, sql, rowCount } = queryData

  if (!data || data.length === 0) return null

  const formatValue = (value: unknown): string => {
    if (value === null || value === undefined) return '-'
    if (typeof value === 'number') {
      if (Number.isInteger(value)) return value.toLocaleString()
      return value.toLocaleString(undefined, { maximumFractionDigits: 2 })
    }
    return String(value)
  }

  return (
    <div className="mt-2.5 space-y-2">
      <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
        <Database className="h-3 w-3" />
        <span>{rowCount} row{rowCount !== 1 ? 's' : ''}</span>
      </div>

      <div className="overflow-x-auto rounded-lg border bg-card">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b bg-muted/40">
              {columns.map((col) => (
                <th key={col} className="px-2.5 py-1.5 text-left font-medium text-muted-foreground whitespace-nowrap">
                  {col.replace(/_/g, ' ')}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.slice(0, 10).map((row, i) => (
              <tr key={i} className={cn('border-t border-border/40', i % 2 === 0 ? '' : 'bg-muted/20')}>
                {columns.map((col) => (
                  <td key={col} className="px-2.5 py-1.5 whitespace-nowrap tabular-nums">
                    {formatValue(row[col])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        {data.length > 10 && (
          <div className="px-2.5 py-1.5 text-[11px] text-muted-foreground bg-muted/30 border-t">
            Showing 10 of {data.length} rows
          </div>
        )}
      </div>

      {sql && (
        <button
          onClick={() => setShowSql(!showSql)}
          className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground transition-colors"
        >
          {showSql ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
          {showSql ? 'Hide' : 'Show'} SQL
        </button>
      )}
      {showSql && sql && (
        <pre className="p-2 bg-muted/50 rounded-lg overflow-x-auto text-[11px] font-mono text-muted-foreground border">
          {sql}
        </pre>
      )}
    </div>
  )
}

function CreatedNotesList({
  notes,
  onOpenNote,
}: {
  notes: CreatedNoteInfo[]
  onOpenNote?: (path: string) => void
}) {
  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr + 'T12:00:00')
    return d.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })
  }

  return (
    <div className="mt-2.5 space-y-1.5">
      <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
        <CalendarPlus className="h-3 w-3" />
        <span>{notes.length} daily note{notes.length !== 1 ? 's' : ''} logged</span>
      </div>
      <div className="grid gap-1">
        {notes.map((note) => (
          <button
            key={note.date}
            type="button"
            onClick={() => onOpenNote?.(note.path)}
            className={cn(
              'flex items-center gap-2 text-left text-xs px-2.5 py-2 rounded-lg border transition-colors',
              'hover:border-teal-500/40 hover:bg-teal-500/5',
            )}
          >
            <span className="font-medium text-foreground">{formatDate(note.date)}</span>
            <span className={cn(
              'ml-auto text-[10px] px-1.5 py-0.5 rounded-full',
              note.created
                ? 'bg-teal-500/10 text-teal-600 dark:text-teal-400'
                : 'bg-amber-500/10 text-amber-600 dark:text-amber-400'
            )}>
              {note.created ? 'new' : 'updated'}
            </span>
          </button>
        ))}
      </div>
    </div>
  )
}

interface ChatMessageProps {
  message: Message
  onOpenNote?: (path: string) => void
}

export function ChatMessage({ message, onOpenNote }: ChatMessageProps) {
  const isUser = message.role === 'user'

  return (
    <div className={cn('flex gap-2.5 px-1', isUser ? '' : '')}>
      <div
        className={cn(
          'flex items-center justify-center h-7 w-7 rounded-lg shrink-0 mt-0.5',
          isUser
            ? 'bg-slate-200 dark:bg-slate-700'
            : 'bg-teal-500/10'
        )}
      >
        {isUser ? (
          <User className="h-3.5 w-3.5 text-slate-600 dark:text-slate-300" />
        ) : (
          <Bot className="h-3.5 w-3.5 text-teal-500" />
        )}
      </div>
      <div className="flex-1 min-w-0 space-y-0.5">
        <div className="flex items-baseline gap-2">
          <span className="text-xs font-semibold">
            {isUser ? 'You' : 'Assistant'}
          </span>
          {message.timestamp && (
            <span className="text-[10px] text-muted-foreground">
              {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
          )}
        </div>
        {message.images && message.images.length > 0 && (
          <div className="flex gap-2 flex-wrap mt-1">
            {message.images.map((img, i) => (
              <img
                key={i}
                src={img.preview || `data:${img.media_type};base64,${img.data}`}
                alt={`Attachment ${i + 1}`}
                className="h-16 w-16 object-cover rounded-lg border"
              />
            ))}
          </div>
        )}
        <div className="text-sm leading-relaxed whitespace-pre-wrap break-words">
          {message.content}
        </div>
        {message.noteUpdated && (
          <div className="flex items-center gap-1.5 text-[11px] text-teal-600 dark:text-teal-400 mt-1">
            <FileCheck className="h-3 w-3" />
            <span>Note updated</span>
          </div>
        )}
        {message.createdNotes && message.createdNotes.length > 0 && (
          <CreatedNotesList notes={message.createdNotes} onOpenNote={onOpenNote} />
        )}
        {message.queryData && <DataTable queryData={message.queryData} />}
      </div>
    </div>
  )
}
