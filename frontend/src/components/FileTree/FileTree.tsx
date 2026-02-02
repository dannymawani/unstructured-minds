import { useState, useEffect, useCallback } from 'react'
import { Plus, FolderPlus, RefreshCw } from 'lucide-react'
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
}

function buildTree(files: FileInfo[]): FileNode[] {
  const nodeMap = new Map<string, FileNode>()
  const roots: FileNode[] = []

  // Sort files so directories come first, then alphabetically
  const sortedFiles = [...files].sort((a, b) => {
    if (a.is_directory !== b.is_directory) {
      return a.is_directory ? -1 : 1
    }
    return a.path.localeCompare(b.path)
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

export function FileTree({
  onFileSelect,
  selectedFile,
  apiBaseUrl = '',
}: FileTreeProps) {
  const [files, setFiles] = useState<FileNode[]>([])
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchFiles = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`${apiBaseUrl}/vault/files`)
      if (!response.ok) {
        throw new Error(`Failed to fetch files: ${response.statusText}`)
      }
      const data = await response.json()
      const tree = buildTree(data.files)
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

  const handleToggle = (path: string) => {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(path)) {
        next.delete(path)
      } else {
        next.add(path)
      }
      return next
    })
  }

  const handleCreateFile = async () => {
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
  }

  const handleCreateFolder = async () => {
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
  }

  const renderTree = (nodes: FileNode[], depth = 0): React.ReactNode => {
    return nodes.map((node) => (
      <div key={node.path} role="group">
        <FileTreeItem
          node={node}
          depth={depth}
          expanded={expanded.has(node.path)}
          selected={selectedFile === node.path}
          onToggle={handleToggle}
          onSelect={onFileSelect}
        />
        {node.isDirectory && expanded.has(node.path) && node.children && (
          renderTree(node.children, depth + 1)
        )}
      </div>
    ))
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-2 py-2 border-b">
        <span className="text-sm font-medium">Files</span>
        <div className="flex gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={handleCreateFile}
            title="New file"
          >
            <Plus className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={handleCreateFolder}
            title="New folder"
          >
            <FolderPlus className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={fetchFiles}
            title="Refresh"
          >
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>
      <div className="flex-1 overflow-auto py-1" role="tree" aria-label="File browser">
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
        {!loading && !error && renderTree(files)}
      </div>
    </div>
  )
}
