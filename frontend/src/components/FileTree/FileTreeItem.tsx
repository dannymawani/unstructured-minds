import { ChevronRight, ChevronDown, Folder, FileText } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface FileNode {
  path: string
  name: string
  isDirectory: boolean
  children?: FileNode[]
}

interface FileTreeItemProps {
  node: FileNode
  depth: number
  expanded: boolean
  selected: boolean
  onToggle: (path: string) => void
  onSelect: (path: string) => void
}

export function FileTreeItem({
  node,
  depth,
  expanded,
  selected,
  onToggle,
  onSelect,
}: FileTreeItemProps) {
  const handleClick = () => {
    if (node.isDirectory) {
      onToggle(node.path)
    } else {
      onSelect(node.path)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      handleClick()
    }
  }

  return (
    <div
      role="treeitem"
      aria-expanded={node.isDirectory ? expanded : undefined}
      aria-selected={selected}
      tabIndex={0}
      className={cn(
        'flex items-center gap-1 px-2 py-1 cursor-pointer text-sm',
        'hover:bg-accent rounded-sm',
        'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1',
        selected && 'bg-accent text-accent-foreground'
      )}
      style={{ paddingLeft: `${depth * 16 + 8}px` }}
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
      <span className="truncate">{node.name}</span>
    </div>
  )
}
