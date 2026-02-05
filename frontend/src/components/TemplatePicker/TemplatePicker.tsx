import { useState, useEffect, useRef, useCallback } from 'react'
import { cn } from '@/lib/utils'
import { FileText, Loader2, FolderPlus } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface Template {
  name: string
  description: string
}

interface TemplatePickerProps {
  isOpen: boolean
  onClose: () => void
  onSelect: (path: string) => void
  apiBaseUrl: string
}

type Step = 'select-template' | 'enter-title'

export function TemplatePicker({ isOpen, onClose, onSelect, apiBaseUrl }: TemplatePickerProps) {
  const [step, setStep] = useState<Step>('select-template')
  const [templates, setTemplates] = useState<Template[]>([])
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null)
  const [title, setTitle] = useState('')
  const [folder, setFolder] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isCreating, setIsCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLDivElement>(null)

  // Fetch templates when opening
  useEffect(() => {
    if (isOpen) {
      setStep('select-template')
      setSelectedIndex(0)
      setSelectedTemplate(null)
      setTitle('')
      setFolder('')
      setError(null)
      fetchTemplates()
    }
  }, [isOpen])

  // Focus input after step change
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 10)
    }
  }, [isOpen, step])

  const fetchTemplates = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await fetch(`${apiBaseUrl}/templates`)
      if (response.ok) {
        const data = await response.json()
        setTemplates(data.templates)
      } else {
        setError('Failed to load templates')
      }
    } catch (err) {
      console.error('Failed to fetch templates:', err)
      setError('Failed to load templates')
    } finally {
      setIsLoading(false)
    }
  }

  const handleSelectTemplate = useCallback(
    (template: Template) => {
      setSelectedTemplate(template)
      setTitle('')
      setStep('enter-title')
    },
    []
  )

  const handleCreate = useCallback(async () => {
    if (!selectedTemplate || !title.trim()) return

    setIsCreating(true)
    setError(null)

    try {
      const response = await fetch(`${apiBaseUrl}/notes/from-template`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          template_name: selectedTemplate.name,
          title: title.trim(),
          folder: folder.trim() || null,
        }),
      })

      if (response.ok) {
        const data = await response.json()
        onSelect(data.path)
        onClose()
      } else {
        const errorData = await response.json()
        setError(errorData.detail || 'Failed to create note')
      }
    } catch (err) {
      console.error('Failed to create note:', err)
      setError('Failed to create note')
    } finally {
      setIsCreating(false)
    }
  }, [selectedTemplate, title, folder, apiBaseUrl, onSelect, onClose])

  // Keyboard navigation for template selection
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (step === 'select-template') {
        switch (e.key) {
          case 'ArrowDown':
            e.preventDefault()
            setSelectedIndex((prev) => (prev < templates.length - 1 ? prev + 1 : 0))
            break
          case 'ArrowUp':
            e.preventDefault()
            setSelectedIndex((prev) => (prev > 0 ? prev - 1 : templates.length - 1))
            break
          case 'Enter':
            e.preventDefault()
            if (templates[selectedIndex]) {
              handleSelectTemplate(templates[selectedIndex])
            }
            break
          case 'Escape':
            e.preventDefault()
            onClose()
            break
        }
      } else if (step === 'enter-title') {
        switch (e.key) {
          case 'Enter':
            e.preventDefault()
            if (title.trim()) {
              handleCreate()
            }
            break
          case 'Escape':
            e.preventDefault()
            setStep('select-template')
            break
        }
      }
    },
    [step, templates, selectedIndex, title, handleSelectTemplate, handleCreate, onClose]
  )

  // Scroll selected item into view
  useEffect(() => {
    if (listRef.current && step === 'select-template') {
      const selectedElement = listRef.current.children[selectedIndex] as HTMLElement
      if (selectedElement) {
        selectedElement.scrollIntoView({ block: 'nearest' })
      }
    }
  }, [selectedIndex, step])

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
        <div className="flex items-center justify-between border-b px-4 py-3">
          <h2 className="text-sm font-medium">
            {step === 'select-template' ? 'New from Template' : `Create from: ${selectedTemplate?.name}`}
          </h2>
          {step === 'enter-title' && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setStep('select-template')}
            >
              Back
            </Button>
          )}
        </div>

        {step === 'select-template' ? (
          <>
            {/* Template list */}
            <div
              ref={listRef}
              className="max-h-[300px] overflow-auto p-2"
              onKeyDown={handleKeyDown}
              tabIndex={0}
            >
              {isLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : error ? (
                <div className="py-6 text-center text-sm text-destructive">{error}</div>
              ) : templates.length === 0 ? (
                <div className="py-6 text-center text-sm text-muted-foreground">
                  No templates found. Create templates in the Templates/ folder.
                </div>
              ) : (
                templates.map((template, index) => (
                  <button
                    key={template.name}
                    className={cn(
                      'flex w-full flex-col items-start gap-1 rounded-md px-3 py-2 text-left',
                      'hover:bg-accent',
                      index === selectedIndex && 'bg-accent'
                    )}
                    onClick={() => handleSelectTemplate(template)}
                    onMouseEnter={() => setSelectedIndex(index)}
                  >
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                      <span className="font-medium capitalize">{template.name}</span>
                    </div>
                    <div className="text-sm text-muted-foreground pl-6">
                      {template.description}
                    </div>
                  </button>
                ))
              )}
            </div>

            {/* Footer with keyboard hints */}
            {templates.length > 0 && (
              <div className="border-t px-3 py-2 text-xs text-muted-foreground flex gap-4">
                <span>
                  <kbd className="rounded bg-muted px-1.5 py-0.5">Enter</kbd> to select
                </span>
                <span>
                  <kbd className="rounded bg-muted px-1.5 py-0.5">Up/Down</kbd> to navigate
                </span>
                <span>
                  <kbd className="rounded bg-muted px-1.5 py-0.5">Esc</kbd> to close
                </span>
              </div>
            )}
          </>
        ) : (
          <>
            {/* Title input form */}
            <div className="p-4 space-y-4">
              <div>
                <label htmlFor="note-title" className="block text-sm font-medium mb-1">
                  Note Title
                </label>
                <input
                  ref={inputRef}
                  id="note-title"
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Enter note title..."
                  className={cn(
                    'w-full rounded-md border px-3 py-2 text-sm',
                    'focus:outline-none focus:ring-2 focus:ring-ring',
                    'bg-background'
                  )}
                  autoFocus
                />
              </div>

              <div>
                <label htmlFor="note-folder" className="block text-sm font-medium mb-1">
                  <div className="flex items-center gap-1">
                    <FolderPlus className="h-4 w-4" />
                    Folder (optional)
                  </div>
                </label>
                <input
                  id="note-folder"
                  type="text"
                  value={folder}
                  onChange={(e) => setFolder(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="e.g., Projects/2026"
                  className={cn(
                    'w-full rounded-md border px-3 py-2 text-sm',
                    'focus:outline-none focus:ring-2 focus:ring-ring',
                    'bg-background'
                  )}
                />
              </div>

              {error && (
                <div className="text-sm text-destructive">{error}</div>
              )}

              <div className="flex justify-end gap-2">
                <Button
                  variant="outline"
                  onClick={() => setStep('select-template')}
                  disabled={isCreating}
                >
                  Back
                </Button>
                <Button
                  onClick={handleCreate}
                  disabled={!title.trim() || isCreating}
                >
                  {isCreating ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                      Creating...
                    </>
                  ) : (
                    'Create Note'
                  )}
                </Button>
              </div>
            </div>

            {/* Footer with keyboard hints */}
            <div className="border-t px-3 py-2 text-xs text-muted-foreground flex gap-4">
              <span>
                <kbd className="rounded bg-muted px-1.5 py-0.5">Enter</kbd> to create
              </span>
              <span>
                <kbd className="rounded bg-muted px-1.5 py-0.5">Esc</kbd> to go back
              </span>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
