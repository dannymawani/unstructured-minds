import { useState, useRef, useEffect, useCallback, type FormEvent, type ClipboardEvent, type ChangeEvent } from 'react'
import { Send, Loader2, Database, MessageSquare, FileText, Paperclip, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ChatMessage, type Message, type QueryData, type ImageAttachment } from './ChatMessage'
import { cn } from '@/lib/utils'

interface ChatPanelProps {
  apiBaseUrl?: string
  currentFile?: string
  currentContent?: string
  onContentUpdate?: (content: string) => void
}

type ChatMode = 'chat' | 'query' | 'note'

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

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const result = reader.result as string
      // Strip the data URL prefix (data:image/png;base64,...)
      resolve(result.split(',')[1])
    }
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

export function ChatPanel({ apiBaseUrl = '', currentFile, currentContent, onContentUpdate }: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [mode, setMode] = useState<ChatMode>(currentFile ? 'note' : 'query')
  const [pendingImages, setPendingImages] = useState<ImageAttachment[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Auto-select note mode when a file is open
  useEffect(() => {
    if (currentFile) {
      setMode('note')
    }
  }, [currentFile])

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

  const addImages = useCallback(async (files: File[]) => {
    const imageFiles = files.filter(f => f.type.startsWith('image/'))
    if (imageFiles.length === 0) return

    const newImages: ImageAttachment[] = await Promise.all(
      imageFiles.map(async (file) => ({
        data: await fileToBase64(file),
        media_type: file.type,
        preview: URL.createObjectURL(file),
      }))
    )
    setPendingImages(prev => [...prev, ...newImages].slice(0, 5))
  }, [])

  const removeImage = useCallback((index: number) => {
    setPendingImages(prev => {
      const removed = prev[index]
      if (removed.preview) URL.revokeObjectURL(removed.preview)
      return prev.filter((_, i) => i !== index)
    })
  }, [])

  const handlePaste = useCallback((e: ClipboardEvent<HTMLTextAreaElement>) => {
    const items = e.clipboardData?.items
    if (!items) return

    const imageFiles: File[] = []
    for (const item of items) {
      if (item.type.startsWith('image/')) {
        const file = item.getAsFile()
        if (file) imageFiles.push(file)
      }
    }
    if (imageFiles.length > 0) {
      e.preventDefault()
      addImages(imageFiles)
    }
  }, [addImages])

  const handleFilePickerChange = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files) addImages(Array.from(files))
    // Reset so the same file can be selected again
    e.target.value = ''
  }, [addImages])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if ((!input.trim() && pendingImages.length === 0) || isLoading) return

    const currentImages = pendingImages.length > 0 ? [...pendingImages] : undefined

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
      images: currentImages,
    }

    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setPendingImages([])
    setError(null)
    setIsLoading(true)

    try {
      if (mode === 'note') {
        // Use note-assist endpoint
        const body: Record<string, unknown> = {
          message: userMessage.content,
          file_path: currentFile || null,
          file_content: currentContent || null,
        }
        if (currentImages) {
          body.images = currentImages.map(img => ({
            data: img.data,
            media_type: img.media_type,
          }))
        }

        const response = await fetch(`${apiBaseUrl}/chat/note-assist`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })

        if (!response.ok) {
          const data = await response.json().catch(() => ({}))
          throw new Error(data.detail || 'Failed to get response')
        }

        const data = await response.json()
        const didUpdate = !!data.updated_content

        if (didUpdate && onContentUpdate) {
          onContentUpdate(data.updated_content)
        }

        const assistantMessage: Message = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: data.reply,
          timestamp: new Date(),
          noteUpdated: didUpdate,
        }

        setMessages((prev) => [...prev, assistantMessage])
      } else if (mode === 'query' || isLikelyDataQuery(userMessage.content)) {
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

  const fileName = currentFile?.split('/').pop()

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-2 border-b">
        <div className="flex items-center justify-between">
          <div className="min-w-0">
            <h2 className="text-sm font-medium">
              {mode === 'note' ? 'Note Assist' : mode === 'query' ? 'Data Query' : 'Chat'}
            </h2>
            <p className="text-xs text-muted-foreground truncate">
              {mode === 'note' && fileName
                ? `Editing: ${fileName}`
                : mode === 'note'
                  ? 'Open a file to get started'
                  : mode === 'query'
                    ? 'Ask questions about your data'
                    : 'General conversation'}
            </p>
          </div>
          <div className="flex gap-1 shrink-0">
            <Button
              variant={mode === 'note' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setMode('note')}
              className="min-w-[44px] min-h-[44px] sm:min-w-0 sm:min-h-0 h-10 sm:h-7 px-3 sm:px-2"
              title="Note Assist Mode"
            >
              <FileText className="h-4 w-4 sm:h-3.5 sm:w-3.5" />
            </Button>
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
              {mode === 'note'
                ? currentFile
                  ? 'Ask me to update your note'
                  : 'Open a file to get started'
                : mode === 'query'
                  ? 'Ask questions about your data'
                  : 'Start a conversation'}
            </p>
            {mode === 'note' && currentFile && (
              <div className="text-xs space-y-1 text-center max-w-[250px]">
                <p className="font-medium text-foreground">Try:</p>
                <p>"Add a task: buy groceries"</p>
                <p>"Log lunch: chicken salad, 450 cal"</p>
                <p>Or paste a screenshot to extract data</p>
              </div>
            )}
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
              {mode === 'note' ? 'Updating note...' : mode === 'query' ? 'Querying data...' : 'Thinking...'}
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

      {/* Pending image thumbnails */}
      {pendingImages.length > 0 && (
        <div className="px-3 py-2 border-t flex gap-2 flex-wrap">
          {pendingImages.map((img, i) => (
            <div key={i} className="relative group">
              <img
                src={img.preview || `data:${img.media_type};base64,${img.data}`}
                alt={`Pending ${i + 1}`}
                className="h-14 w-14 object-cover rounded-md border"
              />
              <button
                type="button"
                onClick={() => removeImage(i)}
                className="absolute -top-1.5 -right-1.5 bg-destructive text-destructive-foreground rounded-full p-0.5 opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          ))}
        </div>
      )}

      <form onSubmit={handleSubmit} className="p-3 border-t safe-area-bottom">
        <div className="flex gap-2">
          {mode === 'note' && (
            <>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                multiple
                className="hidden"
                onChange={handleFilePickerChange}
              />
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => fileInputRef.current?.click()}
                title="Attach image"
                className="min-w-[44px] min-h-[44px] shrink-0"
              >
                <Paperclip className="h-4 w-4" />
              </Button>
            </>
          )}
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            onPaste={mode === 'note' ? handlePaste : undefined}
            placeholder={
              mode === 'note'
                ? 'Update your note...'
                : mode === 'query'
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
            disabled={(!input.trim() && pendingImages.length === 0) || isLoading}
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

      {/* Hidden file input for image picker */}
    </div>
  )
}
