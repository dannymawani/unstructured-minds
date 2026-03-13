import { useState, useRef, useEffect, useCallback, type FormEvent, type ClipboardEvent, type ChangeEvent } from 'react'
import { Send, Loader2, Paperclip, X, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ChatMessage, type Message, type QueryData, type ImageAttachment, type CreatedNoteInfo } from './ChatMessage'
import { cn } from '@/lib/utils'

interface ChatPanelProps {
  apiBaseUrl?: string
  currentFile?: string
  currentContent?: string
  onContentUpdate?: (content: string) => void
  onNotesCreated?: () => void
  onOpenNote?: (path: string) => void
  initialMessage?: string
}

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const result = reader.result as string
      resolve(result.split(',')[1])
    }
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

export function ChatPanel({ apiBaseUrl = '', currentFile, currentContent, onContentUpdate, onNotesCreated, onOpenNote, initialMessage }: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [pendingImages, setPendingImages] = useState<ImageAttachment[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const initialMessageSentRef = useRef<string | null>(null)

  useEffect(() => {
    if (initialMessage && initialMessage !== initialMessageSentRef.current && currentFile && !isLoading) {
      initialMessageSentRef.current = initialMessage
      setInput(initialMessage)
      setTimeout(() => {
        inputRef.current?.form?.requestSubmit()
      }, 100)
    }
  }, [initialMessage, currentFile, isLoading])

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

      const response = await fetch(`${apiBaseUrl}/chat/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        throw new Error(data.detail || 'Failed to get response')
      }

      const data = await response.json()

      if (data.note_update && onContentUpdate) {
        onContentUpdate(data.note_update)
      }

      if (data.created_notes && data.created_notes.length > 0) {
        onNotesCreated?.()
      }

      const queryData: QueryData | undefined =
        data.query_data && data.query_data.columns
          ? {
              columns: data.query_data.columns,
              data: data.query_data.data,
              sql: data.query_data.sql,
              rowCount: data.query_data.row_count,
            }
          : undefined

      const createdNotes: CreatedNoteInfo[] | undefined =
        data.created_notes && data.created_notes.length > 0
          ? data.created_notes
          : undefined

      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: data.reply,
        timestamp: new Date(),
        noteUpdated: !!data.note_update,
        queryData,
        createdNotes,
      }

      setMessages((prev) => [...prev, assistantMessage])
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
    <div className="flex flex-col h-full bg-background">
      {/* Header */}
      <div className="px-5 py-3 border-b bg-card/50 backdrop-blur-sm">
        <div className="flex items-center gap-2.5">
          <div className="flex items-center justify-center h-7 w-7 rounded-lg bg-teal-500/10">
            <Sparkles className="h-4 w-4 text-teal-500" />
          </div>
          <div className="min-w-0">
            <h2 className="text-sm font-semibold leading-none">Chat</h2>
            <p className="text-[11px] text-muted-foreground mt-1 truncate">
              {fileName ? `Editing ${fileName}` : 'Ask anything about your data'}
            </p>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-auto px-4 py-5 space-y-5">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center px-4">
            <div className="space-y-4 max-w-[300px]">
              <div className="flex items-center justify-center h-12 w-12 rounded-2xl bg-teal-500/10 mx-auto">
                <Sparkles className="h-6 w-6 text-teal-500" />
              </div>
              <p className="text-sm text-muted-foreground">What can I help with?</p>
              <div className="grid gap-2">
                {[
                  { label: 'Catch up', example: '"BJJ Monday, rest Tuesday"' },
                  { label: 'Query data', example: '"How did I sleep last week?"' },
                  ...(currentFile ? [{ label: 'Edit note', example: '"Add task: buy groceries"' }] : []),
                ].map((hint) => (
                  <button
                    key={hint.label}
                    type="button"
                    onClick={() => {
                      setInput(hint.example.replace(/"/g, ''))
                      inputRef.current?.focus()
                    }}
                    className="text-left px-4 py-3 rounded-xl border border-border/60 hover:border-teal-500/40 hover:bg-teal-500/5 transition-all group"
                  >
                    <span className="text-xs font-medium text-foreground">{hint.label}</span>
                    <span className="block text-[11px] text-muted-foreground group-hover:text-muted-foreground/80 mt-1">
                      {hint.example}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <ChatMessage key={message.id} message={message} onOpenNote={onOpenNote} />
          ))
        )}
        {isLoading && (
          <div className="flex items-center gap-3 px-2">
            <div className="flex items-center justify-center h-8 w-8 rounded-full bg-teal-500/10 ring-1 ring-teal-500/20">
              <div className="flex gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-teal-500 animate-bounce [animation-delay:0ms]" />
                <span className="w-1.5 h-1.5 rounded-full bg-teal-500 animate-bounce [animation-delay:150ms]" />
                <span className="w-1.5 h-1.5 rounded-full bg-teal-500 animate-bounce [animation-delay:300ms]" />
              </div>
            </div>
            <span className="text-xs text-muted-foreground">Thinking...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Error */}
      {error && (
        <div className="mx-4 mb-3 px-4 py-2.5 text-xs text-rose-600 dark:text-rose-400 bg-rose-500/10 rounded-xl border border-rose-500/20">
          {error}
        </div>
      )}

      {/* Pending images */}
      {pendingImages.length > 0 && (
        <div className="px-4 py-3 border-t flex gap-2.5 flex-wrap">
          {pendingImages.map((img, i) => (
            <div key={i} className="relative group">
              <img
                src={img.preview || `data:${img.media_type};base64,${img.data}`}
                alt={`Pending ${i + 1}`}
                className="h-14 w-14 object-cover rounded-xl border"
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

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t bg-card/30 safe-area-bottom">
        <div className="flex gap-2.5 items-end">
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
            className="min-w-[40px] min-h-[40px] h-10 w-10 shrink-0 rounded-xl text-muted-foreground hover:text-foreground hover:bg-muted/60"
          >
            <Paperclip className="h-4 w-4" />
          </Button>
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            onPaste={handlePaste}
            placeholder="Ask anything about your data..."
            className={cn(
              'flex-1 min-h-[40px] max-h-[120px] resize-none rounded-xl border px-4 py-2.5 text-sm',
              'focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500/50',
              'placeholder:text-muted-foreground/50',
              'bg-background transition-shadow'
            )}
            rows={1}
            disabled={isLoading}
          />
          <Button
            type="submit"
            size="icon"
            disabled={(!input.trim() && pendingImages.length === 0) || isLoading}
            title="Send message"
            className={cn(
              'min-w-[40px] min-h-[40px] h-10 w-10 shrink-0 rounded-xl transition-all',
              input.trim() || pendingImages.length > 0
                ? 'bg-teal-500 hover:bg-teal-600 text-white shadow-sm shadow-teal-500/25'
                : ''
            )}
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
