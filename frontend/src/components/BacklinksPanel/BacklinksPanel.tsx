import { useState, useEffect, useCallback } from 'react'
import { cn } from '@/lib/utils'
import { Link2, FileText, ExternalLink, Loader2 } from 'lucide-react'

interface WikiLink {
  source_path: string
  source_title: string
  target: string
}

interface BacklinksPanelProps {
  currentFile?: string
  onFileSelect: (path: string) => void
  apiBaseUrl: string
}

export function BacklinksPanel({ currentFile, onFileSelect, apiBaseUrl }: BacklinksPanelProps) {
  const [backlinks, setBacklinks] = useState<WikiLink[]>([])
  const [outgoingLinks, setOutgoingLinks] = useState<string[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<'backlinks' | 'outgoing'>('backlinks')

  // Fetch backlinks and outgoing links when file changes
  const fetchLinks = useCallback(async () => {
    if (!currentFile) {
      setBacklinks([])
      setOutgoingLinks([])
      return
    }

    setIsLoading(true)
    try {
      // Fetch both in parallel
      const [backlinksRes, outgoingRes] = await Promise.all([
        fetch(`${apiBaseUrl}/tags/links/backlinks?path=${encodeURIComponent(currentFile)}`),
        fetch(`${apiBaseUrl}/tags/links/outgoing?path=${encodeURIComponent(currentFile)}`),
      ])

      if (backlinksRes.ok) {
        const data = await backlinksRes.json()
        setBacklinks(data.backlinks)
      }

      if (outgoingRes.ok) {
        const data = await outgoingRes.json()
        setOutgoingLinks(data.links)
      }
    } catch (err) {
      console.error('Failed to fetch links:', err)
    } finally {
      setIsLoading(false)
    }
  }, [currentFile, apiBaseUrl])

  useEffect(() => {
    fetchLinks()
  }, [fetchLinks])

  // Handle clicking a backlink
  const handleBacklinkClick = useCallback(
    (path: string) => {
      onFileSelect(path)
    },
    [onFileSelect]
  )

  // Handle clicking an outgoing link
  const handleOutgoingLinkClick = useCallback(
    (linkTarget: string) => {
      // Normalize the link target to a path
      let path = linkTarget.trim()

      // Handle display text (e.g., [[path|display text]])
      if (path.includes('|')) {
        path = path.split('|')[0].trim()
      }

      // Handle anchors (e.g., [[note#section]])
      if (path.includes('#')) {
        path = path.split('#')[0].trim()
      }

      // Add .md extension if missing
      if (!path.endsWith('.md')) {
        path = path + '.md'
      }

      onFileSelect(path)
    },
    [onFileSelect]
  )

  if (!currentFile) {
    return (
      <div className="flex flex-col h-full">
        <div className="flex items-center gap-2 px-2 py-2 border-b">
          <Link2 className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium">Links</span>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <p className="text-sm text-muted-foreground px-4 text-center">
            Select a file to see its links
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header with tabs */}
      <div className="flex items-center gap-1 px-2 py-2 border-b">
        <button
          className={cn(
            'px-2 py-1 text-xs font-medium rounded-md',
            'transition-colors',
            activeTab === 'backlinks'
              ? 'bg-accent text-accent-foreground'
              : 'text-muted-foreground hover:text-foreground hover:bg-accent/50'
          )}
          onClick={() => setActiveTab('backlinks')}
        >
          Backlinks ({backlinks.length})
        </button>
        <button
          className={cn(
            'px-2 py-1 text-xs font-medium rounded-md',
            'transition-colors',
            activeTab === 'outgoing'
              ? 'bg-accent text-accent-foreground'
              : 'text-muted-foreground hover:text-foreground hover:bg-accent/50'
          )}
          onClick={() => setActiveTab('outgoing')}
        >
          Outgoing ({outgoingLinks.length})
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto py-1">
        {isLoading ? (
          <div className="flex items-center justify-center py-4">
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          </div>
        ) : activeTab === 'backlinks' ? (
          // Backlinks list
          backlinks.length === 0 ? (
            <p className="px-4 py-2 text-sm text-muted-foreground">
              No notes link to this file.
            </p>
          ) : (
            backlinks.map((link) => (
              <button
                key={link.source_path}
                className={cn(
                  'flex items-center gap-2 w-full px-2 py-1.5 text-sm',
                  'hover:bg-accent rounded-sm cursor-pointer',
                  'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1'
                )}
                onClick={() => handleBacklinkClick(link.source_path)}
                title={link.source_path}
              >
                <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
                <span className="truncate">{link.source_title}</span>
              </button>
            ))
          )
        ) : (
          // Outgoing links list
          outgoingLinks.length === 0 ? (
            <p className="px-4 py-2 text-sm text-muted-foreground">
              No outgoing links in this file.
            </p>
          ) : (
            outgoingLinks.map((link, index) => (
              <button
                key={`${link}-${index}`}
                className={cn(
                  'flex items-center gap-2 w-full px-2 py-1.5 text-sm',
                  'hover:bg-accent rounded-sm cursor-pointer',
                  'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1'
                )}
                onClick={() => handleOutgoingLinkClick(link)}
                title={`Go to [[${link}]]`}
              >
                <ExternalLink className="h-4 w-4 shrink-0 text-blue-500" />
                <span className="truncate">[[{link}]]</span>
              </button>
            ))
          )
        )}
      </div>
    </div>
  )
}
