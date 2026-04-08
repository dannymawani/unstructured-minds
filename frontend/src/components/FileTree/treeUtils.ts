export interface FileNode {
  path: string
  name: string
  isDirectory: boolean
  children?: FileNode[]
  isVirtual?: boolean
  displayName?: string
}

export interface FileInfo {
  path: string
  name: string
  is_directory: boolean
}

export interface FlattenedNode {
  node: FileNode
  depth: number
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
 * Flatten tree structure for rendering/virtual scrolling.
 * Only includes visible nodes based on expanded state.
 */
export function flattenTree(
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
