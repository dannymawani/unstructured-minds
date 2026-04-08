import { cn } from '@/lib/utils'
import { User, Bot, Database, ChevronDown, ChevronUp, FileCheck } from 'lucide-react'
import { useState } from 'react'

export interface ImageAttachment {
  data: string
  media_type: string
  preview?: string  // object URL for display
}

export interface QueryData {
  columns: string[]
  data: Record<string, unknown>[]
  sql?: string
  rowCount: number
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp?: Date
  queryData?: QueryData
  images?: ImageAttachment[]
  noteUpdated?: boolean
}

interface ChatMessageProps {
  message: Message
}

function DataTable({ queryData }: { queryData: QueryData }) {
  const [showSql, setShowSql] = useState(false)
  const { columns, data, sql, rowCount } = queryData

  if (!data || data.length === 0) {
    return null
  }

  const formatValue = (value: unknown): string => {
    if (value === null || value === undefined) return '-'
    if (typeof value === 'number') {
      // Format numbers nicely
      if (Number.isInteger(value)) return value.toLocaleString()
      return value.toLocaleString(undefined, { maximumFractionDigits: 2 })
    }
    return String(value)
  }

  return (
    <div className="mt-3 space-y-2">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Database className="h-3 w-3" />
        <span>{rowCount} row{rowCount !== 1 ? 's' : ''} returned</span>
      </div>

      <div className="overflow-x-auto rounded-md border">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr>
              {columns.map((col) => (
                <th
                  key={col}
                  className="px-3 py-2 text-left font-medium text-muted-foreground whitespace-nowrap"
                >
                  {col.replace(/_/g, ' ')}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.slice(0, 10).map((row, i) => (
              <tr
                key={i}
                className={cn(
                  'border-t',
                  i % 2 === 0 ? 'bg-background' : 'bg-muted/20'
                )}
              >
                {columns.map((col) => (
                  <td key={col} className="px-3 py-2 whitespace-nowrap">
                    {formatValue(row[col])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        {data.length > 10 && (
          <div className="px-3 py-2 text-xs text-muted-foreground bg-muted/30 border-t">
            Showing 10 of {data.length} rows
          </div>
        )}
      </div>

      {sql && (
        <div className="text-xs">
          <button
            onClick={() => setShowSql(!showSql)}
            className="flex items-center gap-1 text-muted-foreground hover:text-foreground transition-colors"
          >
            {showSql ? (
              <ChevronUp className="h-3 w-3" />
            ) : (
              <ChevronDown className="h-3 w-3" />
            )}
            {showSql ? 'Hide' : 'Show'} SQL query
          </button>
          {showSql && (
            <pre className="mt-2 p-2 bg-muted rounded-md overflow-x-auto text-xs font-mono">
              {sql}
            </pre>
          )}
        </div>
      )}
    </div>
  )
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user'

  return (
    <div
      className={cn(
        'flex gap-3 p-3 rounded-lg',
        isUser ? 'bg-muted/50' : 'bg-background'
      )}
    >
      <div
        className={cn(
          'flex items-center justify-center h-8 w-8 rounded-full shrink-0',
          isUser ? 'bg-primary text-primary-foreground' : 'bg-muted'
        )}
      >
        {isUser ? (
          <User className="h-4 w-4" />
        ) : (
          <Bot className="h-4 w-4" />
        )}
      </div>
      <div className="flex-1 space-y-1 overflow-hidden">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">
            {isUser ? 'You' : 'Assistant'}
          </span>
          {message.timestamp && (
            <span className="text-xs text-muted-foreground">
              {message.timestamp.toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit',
              })}
            </span>
          )}
        </div>
        {message.images && message.images.length > 0 && (
          <div className="flex gap-2 flex-wrap">
            {message.images.map((img, i) => (
              <img
                key={i}
                src={img.preview || `data:${img.media_type};base64,${img.data}`}
                alt={`Attachment ${i + 1}`}
                className="h-16 w-16 object-cover rounded-md border"
              />
            ))}
          </div>
        )}
        <div className="text-sm whitespace-pre-wrap break-words">
          {message.content}
        </div>
        {message.noteUpdated && (
          <div className="flex items-center gap-1.5 text-xs text-teal-600 dark:text-teal-400 mt-1">
            <FileCheck className="h-3.5 w-3.5" />
            <span>Note updated</span>
          </div>
        )}
        {message.queryData && <DataTable queryData={message.queryData} />}
      </div>
    </div>
  )
}
