import { useState, useEffect, useCallback } from 'react'
import { cn } from '@/lib/utils'
import { Hash, FileText, ChevronRight, ChevronDown, RefreshCw, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface TagCount {
  tag: string
  count: number
}

interface NoteInfo {
  path: string
  title: string
}

interface TagsPanelProps {
  onFileSelect: (path: string) => void
  apiBaseUrl: string
}

export function TagsPanel({ onFileSelect, apiBaseUrl }: TagsPanelProps) {
  const [tags, setTags] = useState<TagCount[]>([])
  const [expandedTag, setExpandedTag] = useState<string | null>(null)
  const [tagNotes, setTagNotes] = useState<Map<string, NoteInfo[]>>(new Map())
  const [isLoading, setIsLoading] = useState(true)
  const [isLoadingNotes, setIsLoadingNotes] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Fetch all tags
  const fetchTags = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await fetch(`${apiBaseUrl}/tags`)
      if (!response.ok) {
        throw new Error('Failed to fetch tags')
      }
      const data = await response.json()
      setTags(data.tags)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load tags')
    } finally {
      setIsLoading(false)
    }
  }, [apiBaseUrl])

  // Fetch notes for a specific tag
  const fetchNotesForTag = useCallback(
    async (tag: string) => {
      setIsLoadingNotes(true)
      try {
        const response = await fetch(`${apiBaseUrl}/tags/${encodeURIComponent(tag)}/notes`)
        if (!response.ok) {
          throw new Error('Failed to fetch notes for tag')
        }
        const data = await response.json()
        setTagNotes((prev) => new Map(prev).set(tag, data.notes))
      } catch (err) {
        console.error('Failed to load notes for tag:', err)
      } finally {
        setIsLoadingNotes(false)
      }
    },
    [apiBaseUrl]
  )

  useEffect(() => {
    fetchTags()
  }, [fetchTags])

  // Handle tag expansion
  const handleTagClick = useCallback(
    (tag: string) => {
      if (expandedTag === tag) {
        setExpandedTag(null)
      } else {
        setExpandedTag(tag)
        // Fetch notes if not already loaded
        if (!tagNotes.has(tag)) {
          fetchNotesForTag(tag)
        }
      }
    },
    [expandedTag, tagNotes, fetchNotesForTag]
  )

  // Handle note selection
  const handleNoteClick = useCallback(
    (path: string) => {
      onFileSelect(path)
    },
    [onFileSelect]
  )

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-2 py-2 border-b">
        <span className="text-sm font-medium">Tags</span>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6"
          onClick={fetchTags}
          title="Refresh tags"
          disabled={isLoading}
        >
          <RefreshCw className={cn('h-4 w-4', isLoading && 'animate-spin')} />
        </Button>
      </div>

      <div className="flex-1 overflow-auto py-1">
        {isLoading && tags.length === 0 && (
          <div className="flex items-center justify-center py-4">
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          </div>
        )}

        {error && (
          <p className="px-4 py-2 text-sm text-destructive">{error}</p>
        )}

        {!isLoading && !error && tags.length === 0 && (
          <p className="px-4 py-2 text-sm text-muted-foreground">
            No tags found. Use #tag in your notes.
          </p>
        )}

        {tags.map((tagItem) => (
          <div key={tagItem.tag}>
            <button
              className={cn(
                'flex items-center gap-1 w-full px-2 py-1 text-sm',
                'hover:bg-accent rounded-sm cursor-pointer',
                'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1',
                expandedTag === tagItem.tag && 'bg-accent'
              )}
              onClick={() => handleTagClick(tagItem.tag)}
            >
              {expandedTag === tagItem.tag ? (
                <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
              ) : (
                <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
              )}
              <Hash className="h-4 w-4 shrink-0 text-blue-500" />
              <span className="truncate">{tagItem.tag}</span>
              <span className="ml-auto text-xs text-muted-foreground">
                {tagItem.count}
              </span>
            </button>

            {/* Expanded notes list */}
            {expandedTag === tagItem.tag && (
              <div className="pl-8">
                {isLoadingNotes && !tagNotes.has(tagItem.tag) ? (
                  <div className="flex items-center gap-2 px-2 py-1 text-sm text-muted-foreground">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    Loading...
                  </div>
                ) : (
                  tagNotes.get(tagItem.tag)?.map((note) => (
                    <button
                      key={note.path}
                      className={cn(
                        'flex items-center gap-1 w-full px-2 py-1 text-sm',
                        'hover:bg-accent rounded-sm cursor-pointer',
                        'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1'
                      )}
                      onClick={() => handleNoteClick(note.path)}
                    >
                      <FileText className="h-3 w-3 shrink-0 text-muted-foreground" />
                      <span className="truncate text-xs">{note.title}</span>
                    </button>
                  ))
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
