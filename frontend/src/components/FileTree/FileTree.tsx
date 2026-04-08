import { useState, useEffect, useCallback, useMemo, useRef, memo } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import { Plus, FolderPlus, RefreshCw, FileText, CalendarDays, LayoutTemplate, ChevronDown } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { FileTreeItem, type FileNode } from './FileTreeItem'

interface FileInfo {
  path: string
  name: string
  is_directory: boolean
}

interface FileTreeProps {
  onFileSelect: (path: string) => void
  selectedFile?: string
  apiBaseUrl?: string
  onCreateDailyNote?: () => void
  onOpenTemplatePicker?: () => void
}

interface FlattenedNode {
  node: FileNode
  depth: number
}

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

/**
 * Transform Daily-Notes children from flat YYYY-MM folders
 * into a year > month hierarchy with human-readable month names.
 */
export function transformDailyNotes(roots: FileNode[]): FileNode[] {
  const dailyNotes = roots.find(
    (n) => n.path === 'Daily-Notes' && n.isDirectory
  )
  if (!dailyNotes || !dailyNotes.children) return roots

  // Separate month folders (YYYY-MM) from other children (e.g. Life-Profile.md)
  const monthPattern = /^(\d{4})-(\d{2})$/
  const yearMap = new Map<string, FileNode[]>()
  const otherChildren: FileNode[] = []

  for (const child of dailyNotes.children) {
    const match = child.name.match(monthPattern)
    if (match && child.isDirectory) {
      const year = match[1]
      const monthIdx = parseInt(match[2], 10) - 1
      const displayName = MONTH_NAMES[monthIdx] || child.name
      const transformed: FileNode = {
        ...child,
        displayName,
      }
      if (!yearMap.has(year)) yearMap.set(year, [])
      yearMap.get(year)!.push(transformed)
    } else {
      otherChildren.push(child)
    }
  }

  // Build virtual year nodes, sorted newest first
  const yearNodes: FileNode[] = [...yearMap.entries()]
    .sort((a, b) => b[0].localeCompare(a[0]))
    .map(([year, months]) => ({
      path: `Daily-Notes/__year__/${year}`,
      name: year,
      isDirectory: true,
      isVirtual: true,
      children: months.sort((a, b) => b.path.localeCompare(a.path)),
    }))

  // Non-month children first (files), then year nodes
  dailyNotes.children = [...otherChildren, ...yearNodes]

  return roots
}

export function buildTree(files: FileInfo[]): FileNode[] {
  const nodeMap = new Map<string, FileNode>()
  const roots: FileNode[] = []

  // Sort: directories first, then newest first (reverse alpha for date-based names)
  const sortedFiles = [...files].sort((a, b) => {
    if (a.is_directory !== b.is_directory) {
      return a.is_directory ? -1 : 1
    }
    // Reverse sort so newest dates appear first
    return b.path.localeCompare(a.path)
  })

  for (const file of sortedFiles) {
    const node: FileNode = {
      path: file.path,
      name: file.name,
      isDirectory: file.is_directory,
      children: file.is_directory ? [] : undefined,
    }
    nodeMap.set(file.path, node)

    // Find parent path
    const parts = file.path.split('/')
    if (parts.length === 1) {
      // Top-level item
      roots.push(node)
    } else {
      // Has a parent
      const parentPath = parts.slice(0, -1).join('/')
      const parent = nodeMap.get(parentPath)
      if (parent && parent.children) {
        parent.children.push(node)
      } else {
        // Parent not found, add as root
        roots.push(node)
      }
    }
  }

  return roots
}

/**
 * Flatten tree structure for virtual scrolling
 * Only includes visible nodes based on expanded state
 */
function flattenTree(
  nodes: FileNode[],
  expanded: Set<string>,
  depth = 0
): FlattenedNode[] {
  const result: FlattenedNode[] = []

  for (const node of nodes) {
    result.push({ node, depth })

    if (node.isDirectory && expanded.has(node.path) && node.children) {
      result.push(...flattenTree(node.children, expanded, depth + 1))
    }
  }

  return result
}

// Memoized FileTreeItem to prevent unnecessary re-renders
const MemoizedFileTreeItem = memo(FileTreeItem)

export function FileTree({
  onFileSelect,
  selectedFile,
  apiBaseUrl = '',
  onCreateDailyNote,
  onOpenTemplatePicker,
}: FileTreeProps) {
  const [files, setFiles] = useState<FileNode[]>([])
  const [expanded, setExpanded] = useState<Set<string>>(() => {
    // Auto-expand Daily-Notes, current year, and current month folder on first load
    const now = new Date()
    const year = String(now.getFullYear())
    const month = `${year}-${String(now.getMonth() + 1).padStart(2, '0')}`
    return new Set([
      'Daily-Notes',
      `Daily-Notes/__year__/${year}`,
      `Daily-Notes/${month}`,
    ])
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isNewMenuOpen, setIsNewMenuOpen] = useState(false)
  const newMenuRef = useRef<HTMLDivElement>(null)
  const parentRef = useRef<HTMLDivElement>(null)

  const fetchFiles = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`${apiBaseUrl}/vault/files`)
      if (!response.ok) {
        throw new Error(`Failed to fetch files: ${response.statusText}`)
      }
      const data = await response.json()
      const tree = transformDailyNotes(buildTree(data.files))
      setFiles(tree)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load files')
    } finally {
      setLoading(false)
    }
  }, [apiBaseUrl])

  useEffect(() => {
    fetchFiles()
  }, [fetchFiles])

  // Memoize toggle handler to prevent re-renders
  const handleToggle = useCallback((path: string) => {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(path)) {
        next.delete(path)
      } else {
        next.add(path)
      }
      return next
    })
  }, [])

  // Memoize select handler
  const handleSelect = useCallback(
    (path: string) => {
      onFileSelect(path)
    },
    [onFileSelect]
  )

  const handleCreateFile = useCallback(async () => {
    const name = prompt('Enter file name (e.g., notes/my-note.md):')
    if (!name) return

    const path = name.endsWith('.md') ? name : `${name}.md`
    try {
      const response = await fetch(`${apiBaseUrl}/vault/file`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path, content: `# ${path.split('/').pop()?.replace('.md', '')}\n\n` }),
      })
      if (!response.ok) {
        throw new Error('Failed to create file')
      }
      await fetchFiles()
      onFileSelect(path)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create file')
    }
  }, [apiBaseUrl, fetchFiles, onFileSelect])

  const handleCreateFolder = useCallback(async () => {
    const name = prompt('Enter folder name:')
    if (!name) return

    // Create folder by creating a placeholder file inside it
    const path = `${name}/.gitkeep`
    try {
      const response = await fetch(`${apiBaseUrl}/vault/file`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path, content: '' }),
      })
      if (!response.ok) {
        throw new Error('Failed to create folder')
      }
      await fetchFiles()
      setExpanded((prev) => new Set(prev).add(name))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create folder')
    }
  }, [apiBaseUrl, fetchFiles])

  // Close new menu on click outside
  useEffect(() => {
    if (!isNewMenuOpen) return
    const handleClickOutside = (e: MouseEvent) => {
      if (newMenuRef.current && !newMenuRef.current.contains(e.target as Node)) {
        setIsNewMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isNewMenuOpen])

  // Flatten tree for virtual scrolling - memoized to avoid recomputation
  const flattenedNodes = useMemo(
    () => flattenTree(files, expanded),
    [files, expanded]
  )

  // Virtual scrolling setup
  const virtualizer = useVirtualizer({
    count: flattenedNodes.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 28, // Estimated row height in pixels
    overscan: 10, // Render extra items above/below visible area
  })

  const virtualItems = virtualizer.getVirtualItems()

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-2 py-2 border-b">
        <span className="text-sm font-medium">Files</span>
        <div className="flex gap-1">
          <div className="relative" ref={newMenuRef}>
            <Button
              variant="ghost"
              size="icon"
              className="h-10 w-10 sm:h-6 sm:w-6"
              onClick={() => setIsNewMenuOpen(prev => !prev)}
              title="New note"
            >
              <Plus className="h-4 w-4" />
              <ChevronDown className="h-2.5 w-2.5 ml-0.5" />
            </Button>
            {isNewMenuOpen && (
              <div className="absolute right-0 top-full mt-1 w-48 rounded-md border bg-popover shadow-md z-50">
                <div className="py-1">
                  <button
                    className="flex w-full items-center gap-2 px-3 py-1.5 text-sm hover:bg-accent"
                    onClick={() => { setIsNewMenuOpen(false); handleCreateFile() }}
                  >
                    <FileText className="h-4 w-4 text-muted-foreground" />
                    Blank Note
                  </button>
                  {onCreateDailyNote && (
                    <button
                      className="flex w-full items-center gap-2 px-3 py-1.5 text-sm hover:bg-accent"
                      onClick={() => { setIsNewMenuOpen(false); onCreateDailyNote() }}
                    >
                      <CalendarDays className="h-4 w-4 text-muted-foreground" />
                      Today's Note
                      <span className="ml-auto text-xs text-muted-foreground">Cmd+D</span>
                    </button>
                  )}
                  {onOpenTemplatePicker && (
                    <>
                      <div className="my-1 border-t" />
                      <button
                        className="flex w-full items-center gap-2 px-3 py-1.5 text-sm hover:bg-accent"
                        onClick={() => { setIsNewMenuOpen(false); onOpenTemplatePicker() }}
                      >
                        <LayoutTemplate className="h-4 w-4 text-muted-foreground" />
                        From Template...
                        <span className="ml-auto text-xs text-muted-foreground">Cmd+T</span>
                      </button>
                    </>
                  )}
                </div>
              </div>
            )}
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="h-10 w-10 sm:h-6 sm:w-6"
            onClick={handleCreateFolder}
            title="New folder"
          >
            <FolderPlus className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-10 w-10 sm:h-6 sm:w-6"
            onClick={fetchFiles}
            title="Refresh"
          >
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>
      <div
        ref={parentRef}
        className="flex-1 overflow-auto py-1"
        role="tree"
        aria-label="File browser"
      >
        {loading && (
          <p className="px-4 py-2 text-sm text-muted-foreground">Loading...</p>
        )}
        {error && (
          <p className="px-4 py-2 text-sm text-destructive">{error}</p>
        )}
        {!loading && !error && files.length === 0 && (
          <p className="px-4 py-2 text-sm text-muted-foreground">
            No files yet. Create one to get started.
          </p>
        )}
        {!loading && !error && flattenedNodes.length > 0 && (
          <div
            style={{
              height: `${virtualizer.getTotalSize()}px`,
              width: '100%',
              position: 'relative',
            }}
          >
            {virtualItems.map((virtualItem) => {
              const { node, depth } = flattenedNodes[virtualItem.index]
              return (
                <div
                  key={node.path}
                  role="group"
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: `${virtualItem.size}px`,
                    transform: `translateY(${virtualItem.start}px)`,
                  }}
                >
                  <MemoizedFileTreeItem
                    node={node}
                    depth={depth}
                    expanded={expanded.has(node.path)}
                    selected={selectedFile === node.path}
                    onToggle={handleToggle}
                    onSelect={handleSelect}
                  />
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
