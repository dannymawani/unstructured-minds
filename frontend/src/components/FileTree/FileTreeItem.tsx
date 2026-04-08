import { memo, useCallback, useMemo, useRef, useEffect, useState } from 'react'
import { ChevronRight, ChevronDown, Folder, FileText } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface FileNode {
  path: string
  name: string
  isDirectory: boolean
  children?: FileNode[]
  isVirtual?: boolean
  displayName?: string
}

interface FileTreeItemProps {
  node: FileNode
  depth: number
  expanded: boolean
  selected: boolean
  onToggle: (path: string) => void
  onSelect: (path: string) => void
  onContextMenu?: (e: React.MouseEvent, path: string) => void
  onMoveFile?: (oldPath: string, newParentPath: string) => void
  isRenaming?: boolean
  renameValue?: string
  onRenameChange?: (value: string) => void
  onRenameSubmit?: () => void
  onRenameCancel?: () => void
}

function FileTreeItemComponent({
  node,
  depth,
  expanded,
  selected,
  onToggle,
  onSelect,
  onContextMenu,
  onMoveFile,
  isRenaming,
  renameValue,
  onRenameChange,
  onRenameSubmit,
  onRenameCancel,
}: FileTreeItemProps) {
  const renameInputRef = useRef<HTMLInputElement>(null)
  const [isDragOver, setIsDragOver] = useState(false)
  const [isDragging, setIsDragging] = useState(false)

  useEffect(() => {
    if (isRenaming && renameInputRef.current) {
      renameInputRef.current.focus()
      // Place cursor at end of filename (before extension) without selecting
      const dotIdx = (renameValue ?? '').lastIndexOf('.')
      const cursorPos = dotIdx > 0 ? dotIdx : (renameValue ?? '').length
      renameInputRef.current.setSelectionRange(cursorPos, cursorPos)
    }
  }, [isRenaming, renameValue])

  const handleClick = useCallback(() => {
    if (node.isDirectory) {
      onToggle(node.path)
    } else {
      onSelect(node.path)
    }
  }, [node.isDirectory, node.path, onToggle, onSelect])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault()
        handleClick()
      }
    },
    [handleClick]
  )

  const handleContextMenu = useCallback(
    (e: React.MouseEvent) => {
      if (!node.isDirectory && onContextMenu) {
        e.preventDefault()
        onContextMenu(e, node.path)
      }
    },
    [node.isDirectory, node.path, onContextMenu]
  )

  // Drag and drop handlers
  const handleDragStart = useCallback(
    (e: React.DragEvent) => {
      if (node.isVirtual) {
        e.preventDefault()
        return
      }
      e.dataTransfer.setData('text/plain', node.path)
      e.dataTransfer.effectAllowed = 'move'
      setIsDragging(true)
    },
    [node.path, node.isVirtual]
  )

  const handleDragEnd = useCallback(() => {
    setIsDragging(false)
  }, [])

  const handleDragOver = useCallback(
    (e: React.DragEvent) => {
      if (!node.isDirectory || node.isVirtual) return
      e.preventDefault()
      e.dataTransfer.dropEffect = 'move'
      setIsDragOver(true)
    },
    [node.isDirectory, node.isVirtual]
  )

  const handleDragLeave = useCallback(() => {
    setIsDragOver(false)
  }, [])

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setIsDragOver(false)
      if (!node.isDirectory || node.isVirtual) return

      const sourcePath = e.dataTransfer.getData('text/plain')
      if (!sourcePath || sourcePath === node.path) return

      // Don't allow dropping into own parent (no-op)
      const sourceParent = sourcePath.split('/').slice(0, -1).join('/')
      if (sourceParent === node.path) return

      // Prevent moving a folder into its own subtree
      if (node.path.startsWith(sourcePath + '/')) return

      onMoveFile?.(sourcePath, node.path)
    },
    [node.path, node.isDirectory, node.isVirtual, onMoveFile]
  )

  // Memoize style to avoid object recreation on each render
  const style = useMemo(
    () => ({ paddingLeft: `${depth * 16 + 8}px` }),
    [depth]
  )

  // Memoize className computation
  const className = useMemo(
    () =>
      cn(
        'flex items-center gap-1 px-2 py-1.5 sm:py-0.5 cursor-pointer text-sm',
        'min-h-[44px] sm:min-h-[28px]',
        'hover:bg-accent rounded-sm',
        'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1',
        selected && 'bg-accent text-accent-foreground',
        isDragOver && 'bg-primary/20 ring-1 ring-primary',
        isDragging && 'opacity-50'
      ),
    [selected, isDragOver, isDragging]
  )

  return (
    <div
      role="treeitem"
      aria-expanded={node.isDirectory ? expanded : undefined}
      aria-selected={selected}
      tabIndex={0}
      className={className}
      style={style}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      onContextMenu={handleContextMenu}
      draggable={!node.isVirtual && !isRenaming}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {node.isDirectory ? (
        <>
          {expanded ? (
            <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
          )}
          <Folder className="h-4 w-4 shrink-0 text-muted-foreground" />
        </>
      ) : (
        <>
          <span className="h-4 w-4" />
          <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
        </>
      )}
      {isRenaming ? (
        <input
          ref={renameInputRef}
          className="flex-1 min-w-0 bg-background border border-ring rounded px-1 py-0 text-sm outline-none"
          value={renameValue ?? ''}
          onChange={(e) => onRenameChange?.(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault()
              onRenameSubmit?.()
            } else if (e.key === 'Escape') {
              e.preventDefault()
              onRenameCancel?.()
            }
            e.stopPropagation()
          }}
          onBlur={() => onRenameCancel?.()}
          onClick={(e) => e.stopPropagation()}
        />
      ) : (
        <span className="truncate">{node.displayName || node.name}</span>
      )}
    </div>
  )
}

// Memoize component to prevent re-renders when props haven't changed
export const FileTreeItem = memo(FileTreeItemComponent, (prevProps, nextProps) => {
  // Custom comparison for optimal memoization
  return (
    prevProps.node.path === nextProps.node.path &&
    prevProps.node.name === nextProps.node.name &&
    prevProps.node.isDirectory === nextProps.node.isDirectory &&
    prevProps.node.isVirtual === nextProps.node.isVirtual &&
    prevProps.node.displayName === nextProps.node.displayName &&
    prevProps.depth === nextProps.depth &&
    prevProps.expanded === nextProps.expanded &&
    prevProps.selected === nextProps.selected &&
    prevProps.onToggle === nextProps.onToggle &&
    prevProps.onSelect === nextProps.onSelect &&
    prevProps.onContextMenu === nextProps.onContextMenu &&
    prevProps.onMoveFile === nextProps.onMoveFile &&
    prevProps.isRenaming === nextProps.isRenaming &&
    prevProps.renameValue === nextProps.renameValue
  )
})
