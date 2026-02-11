import { useState, useEffect, useCallback, useMemo, useRef, memo } from 'react'
import { createPortal } from 'react-dom'
import { useVirtualizer } from '@tanstack/react-virtual'
import { Plus, FolderPlus, RefreshCw, FileText, CalendarDays, LayoutTemplate, ChevronDown, Trash2, Pencil, CaseSensitive, Hash } from 'lucide-react'
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
  onDeleteFile?: (path: string) => void
  onRenameFile?: (oldPath: string, newPath: string) => void
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
 * Transform daily note folder structures for display.
 * When showMonthNames is true, renames month folders to human-readable names.
 */
export function transformDailyNotes(roots: FileNode[], showMonthNames = false): FileNode[] {
  // Handle legacy Daily-Notes/YYYY-MM structure
  const dailyNotes = roots.find(
    (n) => n.path === 'Daily-Notes' && n.isDirectory
  )
  if (dailyNotes && dailyNotes.children) {
    const monthPattern = /^(\d{4})-(\d{2})$/
    const yearMap = new Map<string, FileNode[]>()
    const otherChildren: FileNode[] = []

    for (const child of dailyNotes.children) {
      const match = child.name.match(monthPattern)
      if (match && child.isDirectory) {
        const year = match[1]
        if (showMonthNames) {
          const monthIdx = parseInt(match[2], 10) - 1
          child.displayName = MONTH_NAMES[monthIdx] || child.name
        }
        if (!yearMap.has(year)) yearMap.set(year, [])
        yearMap.get(year)!.push(child)
      } else {
        otherChildren.push(child)
      }
    }

    const yearNodes: FileNode[] = [...yearMap.entries()]
      .sort((a, b) => b[0].localeCompare(a[0]))
      .map(([year, months]) => ({
        path: `Daily-Notes/__year__/${year}`,
        name: year,
        isDirectory: true,
        isVirtual: true,
        children: months.sort((a, b) => b.path.localeCompare(a.path)),
      }))

    dailyNotes.children = [...otherChildren, ...yearNodes]
  }

  // Handle new YYYY/MM structure: optionally rename month folders
  if (showMonthNames) {
    const yearPattern = /^\d{4}$/
    const monthFolderPattern = /^(\d{2})$/
    for (const root of roots) {
      if (root.isDirectory && yearPattern.test(root.name) && root.children) {
        for (const child of root.children) {
          const match = child.name.match(monthFolderPattern)
          if (match && child.isDirectory) {
            const monthIdx = parseInt(match[1], 10) - 1
            child.displayName = MONTH_NAMES[monthIdx] || child.name
          }
        }
      }
    }
  }

  return roots
}

export function buildTree(files: FileInfo[]): FileNode[] {
  const nodeMap = new Map<string, FileNode>()
  const roots: FileNode[] = []

  // Sort: directories first (shallow before deep to ensure parents exist in nodeMap),
  // then newest first (reverse alpha for date-based names)
  const sortedFiles = [...files].sort((a, b) => {
    if (a.is_directory !== b.is_directory) {
      return a.is_directory ? -1 : 1
    }
    // For directories, sort shallow-first so parents are processed before children
    if (a.is_directory && b.is_directory) {
      const depthA = a.path.split('/').length
      const depthB = b.path.split('/').length
      if (depthA !== depthB) return depthA - depthB
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
  onDeleteFile,
  onRenameFile,
}: FileTreeProps) {
  const [files, setFiles] = useState<FileNode[]>([])
  const [showMonthNames, setShowMonthNames] = useState(false)

  // Fetch month name preference from settings on mount
  useEffect(() => {
    fetch(`${apiBaseUrl}/settings`)
      .then(r => r.json())
      .then(data => {
        if (typeof data.show_month_names === 'boolean') {
          setShowMonthNames(data.show_month_names)
        }
      })
      .catch(() => {})
  }, [apiBaseUrl])

  const [expanded, setExpanded] = useState<Set<string>>(() => {
    // Auto-expand current year and month folders on first load (both structures)
    const now = new Date()
    const year = String(now.getFullYear())
    const monthStr = String(now.getMonth() + 1).padStart(2, '0')
    return new Set([
      // Legacy Daily-Notes structure
      'Daily-Notes',
      `Daily-Notes/__year__/${year}`,
      `Daily-Notes/${year}-${monthStr}`,
      // New YYYY/MM structure
      year,
      `${year}/${monthStr}`,
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
      const tree = transformDailyNotes(buildTree(data.files), showMonthNames)
      setFiles(tree)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load files')
    } finally {
      setLoading(false)
    }
  }, [apiBaseUrl, showMonthNames])

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

  // Context menu state for file deletion
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; path: string } | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)
  const contextMenuRef = useRef<HTMLDivElement>(null)

  const handleContextMenu = useCallback(
    (e: React.MouseEvent, path: string) => {
      setContextMenu({ x: e.clientX, y: e.clientY, path })
      setDeleteConfirm(null)
    },
    []
  )

  const handleDeleteFile = useCallback(
    async (path: string) => {
      try {
        const response = await fetch(`${apiBaseUrl}/vault/file?path=${encodeURIComponent(path)}`, {
          method: 'DELETE',
        })
        if (!response.ok) {
          throw new Error('Failed to delete file')
        }
        await fetchFiles()
        onDeleteFile?.(path)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to delete file')
      } finally {
        setContextMenu(null)
        setDeleteConfirm(null)
      }
    },
    [apiBaseUrl, fetchFiles, onDeleteFile]
  )

  // Rename state
  const [renamingFile, setRenamingFile] = useState<string | null>(null)
  const [renameValue, setRenameValue] = useState('')

  const handleStartRename = useCallback((path: string) => {
    const fileName = path.split('/').pop() || ''
    setRenamingFile(path)
    setRenameValue(fileName)
    setContextMenu(null)
  }, [])

  const handleRenameSubmit = useCallback(async () => {
    if (!renamingFile || !renameValue.trim()) {
      setRenamingFile(null)
      return
    }

    const oldPath = renamingFile
    const parts = oldPath.split('/')
    parts[parts.length - 1] = renameValue.trim()
    const newPath = parts.join('/')

    if (newPath === oldPath) {
      setRenamingFile(null)
      return
    }

    try {
      const response = await fetch(`${apiBaseUrl}/vault/file`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ old_path: oldPath, new_path: newPath }),
      })
      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        throw new Error(data.detail || 'Failed to rename file')
      }
      await fetchFiles()
      onRenameFile?.(oldPath, newPath)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to rename file')
    } finally {
      setRenamingFile(null)
    }
  }, [renamingFile, renameValue, apiBaseUrl, fetchFiles, onRenameFile])

  const handleRenameCancel = useCallback(() => {
    setRenamingFile(null)
  }, [])

  // Toggle month name display
  const handleToggleMonthNames = useCallback(async () => {
    const newVal = !showMonthNames
    setShowMonthNames(newVal)
    try {
      await fetch(`${apiBaseUrl}/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ show_month_names: newVal }),
      })
    } catch {
      // Ignore save errors
    }
  }, [showMonthNames, apiBaseUrl])

  // Drag and drop: move file to a new folder
  const handleMoveFile = useCallback(
    async (sourcePath: string, targetFolderPath: string) => {
      const fileName = sourcePath.split('/').pop()
      if (!fileName) return

      const newPath = `${targetFolderPath}/${fileName}`
      if (newPath === sourcePath) return

      try {
        const response = await fetch(`${apiBaseUrl}/vault/file`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ old_path: sourcePath, new_path: newPath }),
        })
        if (!response.ok) {
          const data = await response.json().catch(() => ({}))
          throw new Error(data.detail || 'Failed to move file')
        }
        await fetchFiles()
        onRenameFile?.(sourcePath, newPath)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to move file')
      }
    },
    [apiBaseUrl, fetchFiles, onRenameFile]
  )

  // Close context menu on click outside or Escape
  useEffect(() => {
    if (!contextMenu) return
    const handleClickOutside = (e: MouseEvent) => {
      if (contextMenuRef.current && !contextMenuRef.current.contains(e.target as Node)) {
        setContextMenu(null)
        setDeleteConfirm(null)
      }
    }
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setContextMenu(null)
        setDeleteConfirm(null)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('keydown', handleEscape)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleEscape)
    }
  }, [contextMenu])

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
            className={`h-10 w-10 sm:h-6 sm:w-6 ${showMonthNames ? 'text-primary' : ''}`}
            onClick={handleToggleMonthNames}
            title={showMonthNames ? 'Show month numbers' : 'Show month names'}
          >
            <CaseSensitive className="h-4 w-4" />
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
                    onContextMenu={handleContextMenu}
                    onMoveFile={handleMoveFile}
                    isRenaming={renamingFile === node.path}
                    renameValue={renamingFile === node.path ? renameValue : undefined}
                    onRenameChange={setRenameValue}
                    onRenameSubmit={handleRenameSubmit}
                    onRenameCancel={handleRenameCancel}
                  />
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Context menu portal */}
      {contextMenu && createPortal(
        <div
          ref={contextMenuRef}
          className="fixed z-[9999] min-w-[160px] rounded-md border bg-popover shadow-md"
          style={{ top: contextMenu.y, left: contextMenu.x }}
        >
          {deleteConfirm === contextMenu.path ? (
            <div className="p-2">
              <p className="text-sm mb-2 px-1">
                Delete <span className="font-medium">{contextMenu.path.split('/').pop()}</span>?
              </p>
              <div className="flex gap-1">
                <button
                  className="flex-1 px-2 py-1 text-xs rounded hover:bg-accent"
                  onClick={() => { setContextMenu(null); setDeleteConfirm(null) }}
                >
                  Cancel
                </button>
                <button
                  className="flex-1 px-2 py-1 text-xs rounded bg-destructive text-destructive-foreground hover:bg-destructive/90"
                  onClick={() => handleDeleteFile(contextMenu.path)}
                >
                  Delete
                </button>
              </div>
            </div>
          ) : (
            <div className="py-1">
              <button
                className="flex w-full items-center gap-2 px-3 py-1.5 text-sm hover:bg-accent"
                onClick={() => handleStartRename(contextMenu.path)}
              >
                <Pencil className="h-4 w-4" />
                Rename
              </button>
              <button
                className="flex w-full items-center gap-2 px-3 py-1.5 text-sm hover:bg-accent text-destructive"
                onClick={() => setDeleteConfirm(contextMenu.path)}
              >
                <Trash2 className="h-4 w-4" />
                Delete
              </button>
            </div>
          )}
        </div>,
        document.body
      )}
    </div>
  )
}
