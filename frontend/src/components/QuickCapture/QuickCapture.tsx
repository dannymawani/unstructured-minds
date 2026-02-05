import { useState, useEffect, useRef, useCallback } from 'react'
import { cn } from '@/lib/utils'
import { Zap } from 'lucide-react'

interface QuickCaptureProps {
  isOpen: boolean
  onClose: () => void
  apiBaseUrl: string
  onSuccess?: (path: string) => void
}

export function QuickCapture({
  isOpen,
  onClose,
  apiBaseUrl,
  onSuccess,
}: QuickCaptureProps) {
  const [text, setText] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Reset state and focus when opening
  useEffect(() => {
    if (isOpen) {
      setText('')
      setError(null)
      // Focus textarea after a short delay to ensure modal is rendered
      setTimeout(() => textareaRef.current?.focus(), 10)
    }
  }, [isOpen])

  const handleSubmit = useCallback(async () => {
    if (!text.trim() || isSubmitting) return

    setIsSubmitting(true)
    setError(null)

    try {
      const response = await fetch(`${apiBaseUrl}/vault/quick-capture`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text.trim() }),
      })

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        throw new Error(data.detail || 'Failed to save quick capture')
      }

      const result = await response.json()

      if (result.success) {
        onSuccess?.(result.path)
        onClose()
      } else {
        throw new Error('Failed to save quick capture')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save')
    } finally {
      setIsSubmitting(false)
    }
  }, [text, isSubmitting, apiBaseUrl, onSuccess, onClose])

  // Keyboard handling
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      // Enter (without Shift) to submit
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSubmit()
        return
      }
      // Escape to close
      if (e.key === 'Escape') {
        e.preventDefault()
        onClose()
        return
      }
    },
    [handleSubmit, onClose]
  )

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh]"
      onClick={onClose}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" />

      {/* Modal */}
      <div
        className={cn(
          'relative w-full max-w-lg rounded-lg border bg-background shadow-lg',
          'animate-in fade-in-0 zoom-in-95 duration-150'
        )}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center gap-2 border-b px-4 py-3">
          <Zap className="h-4 w-4 text-amber-500" />
          <span className="font-medium">Quick Capture</span>
          <span className="ml-auto text-xs text-muted-foreground">
            Enter to save, Escape to cancel
          </span>
        </div>

        {/* Textarea */}
        <div className="p-4">
          <textarea
            ref={textareaRef}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your note... (Shift+Enter for new line)"
            rows={3}
            disabled={isSubmitting}
            className={cn(
              'w-full resize-none rounded-md border bg-transparent px-3 py-2 text-sm',
              'focus:outline-none focus:ring-2 focus:ring-ring',
              'placeholder:text-muted-foreground',
              'disabled:cursor-not-allowed disabled:opacity-50'
            )}
          />
          {error && (
            <p className="mt-2 text-sm text-destructive">{error}</p>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t px-4 py-3">
          <span className="text-xs text-muted-foreground">
            Appends to today's daily note
          </span>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className={cn(
                'rounded-md px-3 py-1.5 text-sm font-medium',
                'hover:bg-accent',
                'disabled:cursor-not-allowed disabled:opacity-50'
              )}
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={!text.trim() || isSubmitting}
              className={cn(
                'rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground',
                'hover:bg-primary/90',
                'disabled:cursor-not-allowed disabled:opacity-50'
              )}
            >
              {isSubmitting ? 'Saving...' : 'Save'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
