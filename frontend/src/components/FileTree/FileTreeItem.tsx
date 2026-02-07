import { memo, useCallback, useMemo } from 'react'
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
}

function FileTreeItemComponent({
  node,
  depth,
  expanded,
  selected,
  onToggle,
  onSelect,
}: FileTreeItemProps) {
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
        selected && 'bg-accent text-accent-foreground'
      ),
    [selected]
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
      <span className="truncate">{node.displayName || node.name}</span>
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
    prevProps.onSelect === nextProps.onSelect
  )
})
