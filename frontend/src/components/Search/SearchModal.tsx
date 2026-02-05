import { useState, useEffect, useRef, useCallback } from 'react'
import { cn } from '@/lib/utils'
import { Search, FileText, Loader2 } from 'lucide-react'

interface SearchResult {
  path: string
  title: string
  snippet: string
  score: number
}

interface SearchModalProps {
  isOpen: boolean
  onClose: () => void
  onSelect: (path: string) => void
  apiBaseUrl: string
}

export function SearchModal({ isOpen, onClose, onSelect, apiBaseUrl }: SearchModalProps) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [isLoading, setIsLoading] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLDivElement>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Reset state when opening
  useEffect(() => {
    if (isOpen) {
      setQuery('')
      setResults([])
      setSelectedIndex(0)
      setIsLoading(false)
      setTimeout(() => inputRef.current?.focus(), 10)
    }
  }, [isOpen])

  // Search function
  const performSearch = useCallback(
    async (searchQuery: string) => {
      if (!searchQuery.trim()) {
        setResults([])
        return
      }

      setIsLoading(true)
      try {
        const response = await fetch(`${apiBaseUrl}/search`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: searchQuery, limit: 20 }),
        })
        if (response.ok) {
          const data = await response.json()
          setResults(data.results)
          setSelectedIndex(0)
        }
      } catch (err) {
        console.error('Search failed:', err)
        setResults([])
      } finally {
        setIsLoading(false)
      }
    },
    [apiBaseUrl]
  )

  // Debounced search on query change
  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current)
    }

    debounceRef.current = setTimeout(() => {
      performSearch(query)
    }, 200)

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current)
      }
    }
  }, [query, performSearch])

  // Keyboard navigation
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault()
          setSelectedIndex((prev) => (prev < results.length - 1 ? prev + 1 : 0))
          break
        case 'ArrowUp':
          e.preventDefault()
          setSelectedIndex((prev) => (prev > 0 ? prev - 1 : results.length - 1))
          break
        case 'Enter':
          e.preventDefault()
          if (results[selectedIndex]) {
            onSelect(results[selectedIndex].path)
            onClose()
          }
          break
        case 'Escape':
          e.preventDefault()
          onClose()
          break
      }
    },
    [results, selectedIndex, onSelect, onClose]
  )

  // Scroll selected item into view
  useEffect(() => {
    if (listRef.current) {
      const selectedElement = listRef.current.children[selectedIndex] as HTMLElement
      if (selectedElement) {
        selectedElement.scrollIntoView({ block: 'nearest' })
      }
    }
  }, [selectedIndex])

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
          'relative w-full max-w-2xl rounded-lg border bg-background shadow-lg',
          'animate-in fade-in-0 zoom-in-95 duration-150'
        )}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search input */}
        <div className="flex items-center border-b px-3">
          <Search className="h-4 w-4 text-muted-foreground" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search notes..."
            className={cn(
              'flex-1 bg-transparent px-3 py-3 text-sm',
              'focus:outline-none placeholder:text-muted-foreground'
            )}
          />
          {isLoading && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
        </div>

        {/* Results list */}
        <div ref={listRef} className="max-h-[400px] overflow-auto p-2">
          {query && !isLoading && results.length === 0 ? (
            <div className="py-6 text-center text-sm text-muted-foreground">
              No results found for "{query}"
            </div>
          ) : !query ? (
            <div className="py-6 text-center text-sm text-muted-foreground">
              Start typing to search across your notes
            </div>
          ) : (
            results.map((result, index) => (
              <button
                key={result.path}
                className={cn(
                  'flex w-full flex-col items-start gap-1 rounded-md px-3 py-2 text-left',
                  'hover:bg-accent',
                  index === selectedIndex && 'bg-accent'
                )}
                onClick={() => {
                  onSelect(result.path)
                  onClose()
                }}
                onMouseEnter={() => setSelectedIndex(index)}
              >
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                  <span className="font-medium">{result.title}</span>
                  <span className="text-xs text-muted-foreground">
                    {Math.round(result.score * 100)}% match
                  </span>
                </div>
                <div
                  className="text-sm text-muted-foreground line-clamp-2 pl-6"
                  dangerouslySetInnerHTML={{
                    __html: result.snippet
                      .replace(/\*\*(.+?)\*\*/g, '<mark class="bg-yellow-200 dark:bg-yellow-800 px-0.5 rounded">$1</mark>')
                  }}
                />
                <div className="text-xs text-muted-foreground/70 pl-6">
                  {result.path}
                </div>
              </button>
            ))
          )}
        </div>

        {/* Footer with keyboard hints */}
        {results.length > 0 && (
          <div className="border-t px-3 py-2 text-xs text-muted-foreground flex gap-4">
            <span>
              <kbd className="rounded bg-muted px-1.5 py-0.5">Enter</kbd> to open
            </span>
            <span>
              <kbd className="rounded bg-muted px-1.5 py-0.5">Up/Down</kbd> to navigate
            </span>
            <span>
              <kbd className="rounded bg-muted px-1.5 py-0.5">Esc</kbd> to close
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
