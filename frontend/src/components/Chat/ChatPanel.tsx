import { useState, useRef, useEffect, useCallback, type FormEvent } from 'react'
import { Send, Loader2, Database, MessageSquare } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ChatMessage, type Message, type QueryData } from './ChatMessage'
import { cn } from '@/lib/utils'

interface ChatPanelProps {
  apiBaseUrl?: string
}

type ChatMode = 'chat' | 'query'

// Keywords that suggest a data query
const DATA_QUERY_KEYWORDS = [
  'how much',
  'how many',
  'show me',
  'show my',
  'what was',
  'what is',
  'what are',
  'when did',
  'list',
  'average',
  'total',
  'sum',
  'count',
  'max',
  'min',
  'heaviest',
  'lightest',
  'longest',
  'shortest',
  'last week',
  'this week',
  'last month',
  'this month',
  'yesterday',
  'today',
  'exercise',
  'workout',
  'sleep',
  'food',
  'calories',
  'weight',
  'task',
  'squat',
  'bench',
  'deadlift',
]

function isLikelyDataQuery(input: string): boolean {
  const lowerInput = input.toLowerCase()
  return DATA_QUERY_KEYWORDS.some((keyword) => lowerInput.includes(keyword))
}

export function ChatPanel({ apiBaseUrl = '' }: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [mode, setMode] = useState<ChatMode>('query')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setError(null)
    setIsLoading(true)

    // Determine which endpoint to use
    const shouldUseQueryEndpoint =
      mode === 'query' || isLikelyDataQuery(userMessage.content)

    try {
      if (shouldUseQueryEndpoint) {
        // Use natural language query endpoint
        const response = await fetch(`${apiBaseUrl}/query/natural`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question: userMessage.content }),
        })

        if (!response.ok) {
          const data = await response.json().catch(() => ({}))
          throw new Error(data.detail || 'Failed to get response')
        }

        const data = await response.json()

        const queryData: QueryData | undefined =
          data.data && data.columns
            ? {
                columns: data.columns,
                data: data.data,
                sql: data.sql,
                rowCount: data.row_count,
              }
            : undefined

        const assistantMessage: Message = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: data.answer,
          timestamp: new Date(),
          queryData,
        }

        setMessages((prev) => [...prev, assistantMessage])
      } else {
        // Use regular chat endpoint
        const response = await fetch(`${apiBaseUrl}/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: userMessage.content }),
        })

        if (!response.ok) {
          const data = await response.json().catch(() => ({}))
          throw new Error(data.detail || 'Failed to get response')
        }

        const data = await response.json()

        const assistantMessage: Message = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: data.message.content,
          timestamp: new Date(),
        }

        setMessages((prev) => [...prev, assistantMessage])
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setIsLoading(false)
      inputRef.current?.focus()
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-2 border-b">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-medium">
              {mode === 'query' ? 'Data Query' : 'Chat'}
            </h2>
            <p className="text-xs text-muted-foreground">
              {mode === 'query'
                ? 'Ask questions about your data'
                : 'General conversation'}
            </p>
          </div>
          <div className="flex gap-1">
            <Button
              variant={mode === 'query' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setMode('query')}
              className="min-w-[44px] min-h-[44px] sm:min-w-0 sm:min-h-0 h-10 sm:h-7 px-3 sm:px-2"
              title="Data Query Mode"
            >
              <Database className="h-4 w-4 sm:h-3.5 sm:w-3.5" />
            </Button>
            <Button
              variant={mode === 'chat' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setMode('chat')}
              className="min-w-[44px] min-h-[44px] sm:min-w-0 sm:min-h-0 h-10 sm:h-7 px-3 sm:px-2"
              title="Chat Mode"
            >
              <MessageSquare className="h-4 w-4 sm:h-3.5 sm:w-3.5" />
            </Button>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-2 space-y-2">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-muted-foreground text-sm space-y-4">
            <p>
              {mode === 'query'
                ? 'Ask questions about your data'
                : 'Start a conversation'}
            </p>
            {mode === 'query' && (
              <div className="text-xs space-y-1 text-center max-w-[250px]">
                <p className="font-medium text-foreground">Try asking:</p>
                <p>"How much did I sleep last week?"</p>
                <p>"What was my heaviest squat?"</p>
                <p>"Show my exercise frequency"</p>
              </div>
            )}
          </div>
        ) : (
          messages.map((message) => (
            <ChatMessage key={message.id} message={message} />
          ))
        )}
        {isLoading && (
          <div className="flex items-center gap-2 p-3 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span className="text-sm">
              {mode === 'query' ? 'Querying data...' : 'Thinking...'}
            </span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {error && (
        <div className="px-3 py-2 text-sm text-destructive bg-destructive/10">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="p-3 border-t safe-area-bottom">
        <div className="flex gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              mode === 'query'
                ? 'Ask about your data...'
                : 'Ask a question...'
            }
            className={cn(
              'flex-1 min-h-[44px] max-h-[120px] resize-none rounded-md border px-3 py-2 text-base sm:text-sm',
              'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1',
              'placeholder:text-muted-foreground',
              'bg-background'
            )}
            rows={1}
            disabled={isLoading}
          />
          <Button
            type="submit"
            size="icon"
            disabled={!input.trim() || isLoading}
            title="Send message"
            className="min-w-[44px] min-h-[44px]"
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
      </form>
    </div>
  )
}
