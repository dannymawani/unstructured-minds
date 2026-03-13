import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { ChevronRight, ChevronDown, Folder, PenLine, Plus, Trash2, Filter } from 'lucide-react'
import { cn } from '@/lib/utils'
import { api } from '@/lib/apiClient'
import { buildTree, flattenTree, type FileNode } from '@/components/FileTree'

const QUICK_NOTES_DIR = 'Quick-Notes'

interface QuickNotesProps {
  onFileSelect: (path: string) => void
  selectedFile?: string
  refreshTrigger?: number
}

function loadSectionExpanded(): boolean {
  try {
    const v = localStorage.getItem('quick-notes-section-expanded')
    return v !== null ? v === 'true' : true
  } catch { return true }
}

function loadFolderExpanded(): Set<string> {
  try {
    const v = localStorage.getItem('quick-notes-folders-expanded')
    return v ? new Set(JSON.parse(v)) : new Set()
  } catch { return new Set() }
}

function countNotes(node: FileNode): number {
  if (!node.isDirectory) return 1
  return (node.children || []).reduce((sum, c) => sum + countNotes(c), 0)
}

function sortTree(nodes: FileNode[]): FileNode[] {
  const sorted = [...nodes].sort((a, b) => {
    if (a.isDirectory !== b.isDirectory) return a.isDirectory ? -1 : 1
    return a.name.localeCompare(b.name)
  })
  for (const node of sorted) {
    if (node.children) node.children = sortTree(node.children)
  }
  return sorted
}

function filterTree(nodes: FileNode[], query: string): FileNode[] {
  const q = query.toLowerCase()
  return nodes.reduce<FileNode[]>((acc, node) => {
    if (node.isDirectory) {
      const filtered = filterTree(node.children || [], query)
      if (filtered.length > 0) acc.push({ ...node, children: filtered })
    } else {
      if (node.name.toLowerCase().includes(q)) acc.push(node)
    }
    return acc
  }, [])
}

function collectFolders(nodes: FileNode[]): string[] {
  const result: string[] = []
  for (const node of nodes) {
    if (node.isDirectory) {
      result.push(node.path)
      if (node.children) result.push(...collectFolders(node.children))
    }
  }
  return result
}

export function QuickNotes({ onFileSelect, selectedFile, refreshTrigger }: QuickNotesProps) {
  const [sectionExpanded, setSectionExpanded] = useState(loadSectionExpanded)
  const [expanded, setExpanded] = useState(loadFolderExpanded)
  const [isFilterVisible, setIsFilterVisible] = useState(false)
  const [filterText, setFilterText] = useState('')
  const [isCreating, setIsCreating] = useState(false)
  const [createFolder, setCreateFolder] = useState('')
  const [newFolderName, setNewFolderName] = useState('')
  const [newName, setNewName] = useState('')
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const [tree, setTree] = useState<FileNode[]>([])

  const filterRef = useRef<HTMLInputElement>(null)
  const nameInputRef = useRef<HTMLInputElement>(null)
  const folderInputRef = useRef<HTMLInputElement>(null)

  // Persist section state
  useEffect(() => {
    localStorage.setItem('quick-notes-section-expanded', String(sectionExpanded))
  }, [sectionExpanded])

  // Persist folder expanded state
  useEffect(() => {
    localStorage.setItem('quick-notes-folders-expanded', JSON.stringify([...expanded]))
  }, [expanded])

  useEffect(() => {
    if (isFilterVisible) setTimeout(() => filterRef.current?.focus(), 10)
  }, [isFilterVisible])

  useEffect(() => {
    if (isCreating) setTimeout(() => nameInputRef.current?.focus(), 10)
  }, [isCreating])

  useEffect(() => {
    if (createFolder === '__new__') setTimeout(() => folderInputRef.current?.focus(), 10)
  }, [createFolder])

  const fetchNotes = useCallback(async () => {
    try {
      const data = await api.get<{ files: Array<{ path: string; name: string; is_directory: boolean }> }>('/vault/files')
      const quickFiles = data.files.filter(
        f => (f.path === QUICK_NOTES_DIR || f.path.startsWith(QUICK_NOTES_DIR + '/')) && f.name !== '.gitkeep'
      )
      const fullTree = buildTree(quickFiles)
      const root = fullTree.find(n => n.path === QUICK_NOTES_DIR)
      setTree(sortTree(root?.children || []))
    } catch { /* silently fail */ }
  }, [])

  useEffect(() => { fetchNotes() }, [fetchNotes, refreshTrigger])

  const folders = useMemo(() => collectFolders(tree), [tree])

  const displayTree = useMemo(() => {
    if (!filterText.trim()) return tree
    return filterTree(tree, filterText.trim())
  }, [tree, filterText])

  const effectiveExpanded = useMemo(() => {
    if (filterText.trim()) {
      const all = new Set<string>()
      const addAll = (nodes: FileNode[]) => {
        for (const n of nodes) {
          if (n.isDirectory) {
            all.add(n.path)
            if (n.children) addAll(n.children)
          }
        }
      }
      addAll(displayTree)
      return all
    }
    return expanded
  }, [filterText, expanded, displayTree])

  const flattened = useMemo(
    () => flattenTree(displayTree, effectiveExpanded),
    [displayTree, effectiveExpanded]
  )

  const toggleSection = useCallback(() => setSectionExpanded(prev => !prev), [])

  const toggleFolder = useCallback((path: string) => {
    setExpanded(prev => {
      const next = new Set(prev)
      if (next.has(path)) next.delete(path)
      else next.add(path)
      return next
    })
  }, [])

  const toggleFilter = useCallback(() => {
    setIsFilterVisible(prev => {
      if (prev) setFilterText('')
      return !prev
    })
  }, [])

  const cancelCreate = useCallback(() => {
    setIsCreating(false)
    setCreateFolder('')
    setNewFolderName('')
    setNewName('')
  }, [])

  const startCreate = useCallback(() => {
    setIsCreating(true)
    setCreateFolder('')
    setNewFolderName('')
    setNewName('')
  }, [])

  const handleCreate = useCallback(async () => {
    const name = newName.trim()
    if (!name) { cancelCreate(); return }

    let folder = createFolder
    if (folder === '__new__') {
      const fn = newFolderName.trim()
      if (!fn) return
      folder = `${QUICK_NOTES_DIR}/${fn}`
    } else if (!folder) {
      folder = QUICK_NOTES_DIR
    }

    const path = `${folder}/${name}.md`
    try {
      await api.post('/vault/file', { path, content: `# ${name}\n\n` })
      cancelCreate()
      await fetchNotes()
      onFileSelect(path)
      if (folder !== QUICK_NOTES_DIR) {
        setExpanded(prev => new Set(prev).add(folder))
      }
    } catch { /* silently fail */ }
  }, [newName, createFolder, newFolderName, cancelCreate, fetchNotes, onFileSelect])

  const handleDelete = useCallback(async (path: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (deleteTarget !== path) { setDeleteTarget(path); return }
    try {
      await api.delete(`/vault/file?path=${encodeURIComponent(path)}`)
      setDeleteTarget(null)
      await fetchNotes()
    } catch { /* silently fail */ }
  }, [deleteTarget, fetchNotes])

  const handleNameKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter') { e.preventDefault(); handleCreate() }
    else if (e.key === 'Escape') cancelCreate()
  }, [handleCreate, cancelCreate])

  const handleFolderNameKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter') { e.preventDefault(); nameInputRef.current?.focus() }
    else if (e.key === 'Escape') cancelCreate()
  }, [cancelCreate])

  return (
    <div className="flex flex-col min-h-0" role="tree" aria-label="Quick notes">
      {/* Header */}
      <div className="flex items-center gap-2 px-3 pt-3 pb-1 shrink-0">
        <button
          onClick={toggleSection}
          className="flex items-center gap-1 text-muted-foreground/50 hover:text-muted-foreground transition-colors"
        >
          {sectionExpanded
            ? <ChevronDown className="h-3 w-3" />
            : <ChevronRight className="h-3 w-3" />}
          <span className="text-[10px] font-medium uppercase tracking-widest select-none">
            Quick Notes
          </span>
        </button>
        <div className="flex-1 h-px bg-border/30" />
        {sectionExpanded && (
          <>
            <button
              onClick={toggleFilter}
              className={cn(
                'flex items-center justify-center h-5 w-5 rounded-sm transition-colors',
                isFilterVisible
                  ? 'text-foreground bg-accent/60'
                  : 'text-muted-foreground/40 hover:text-foreground hover:bg-accent/60',
              )}
              title="Filter notes"
            >
              <Filter className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={startCreate}
              className="flex items-center justify-center h-5 w-5 rounded-sm text-muted-foreground/40 hover:text-foreground hover:bg-accent/60 transition-colors"
              title="New quick note"
            >
              <Plus className="h-3.5 w-3.5" />
            </button>
          </>
        )}
      </div>

      {sectionExpanded && (
        <div className="overflow-auto min-h-0 pb-2">
          {/* Filter */}
          {isFilterVisible && (
            <div className="px-3 pb-1">
              <input
                ref={filterRef}
                value={filterText}
                onChange={e => setFilterText(e.target.value)}
                onKeyDown={e => { if (e.key === 'Escape') { setIsFilterVisible(false); setFilterText('') } }}
                placeholder="Filter notes…"
                className="w-full text-xs bg-accent/40 rounded-sm px-2 py-1 outline-none placeholder:text-muted-foreground/40 border border-transparent focus:border-border/50"
              />
            </div>
          )}

          {/* Create form */}
          {isCreating && (
            <div className="px-2 pb-1 space-y-1">
              <div className="flex items-center gap-1 mx-1">
                <select
                  value={createFolder}
                  onChange={e => setCreateFolder(e.target.value)}
                  className="text-xs bg-accent/40 text-foreground rounded-sm px-1.5 py-1 outline-none border border-transparent focus:border-border/50 min-w-0 max-w-[45%]"
                >
                  <option value="">(root)</option>
                  {folders.map(f => (
                    <option key={f} value={f}>{f.replace(QUICK_NOTES_DIR + '/', '')}</option>
                  ))}
                  <option value="__new__">New folder…</option>
                </select>
                <input
                  ref={nameInputRef}
                  value={newName}
                  onChange={e => setNewName(e.target.value)}
                  onKeyDown={handleNameKeyDown}
                  placeholder="Note title…"
                  className="flex-1 min-w-0 text-xs bg-accent/40 rounded-sm px-2 py-1 outline-none placeholder:text-muted-foreground/40 border border-transparent focus:border-border/50"
                />
              </div>
              {createFolder === '__new__' && (
                <div className="mx-1">
                  <input
                    ref={folderInputRef}
                    value={newFolderName}
                    onChange={e => setNewFolderName(e.target.value)}
                    onKeyDown={handleFolderNameKeyDown}
                    placeholder="Folder name…"
                    className="w-full text-xs bg-accent/40 rounded-sm px-2 py-1 outline-none placeholder:text-muted-foreground/40 border border-transparent focus:border-border/50"
                  />
                </div>
              )}
            </div>
          )}

          {/* Tree items */}
          {flattened.map(({ node, depth }) => {
            if (node.isDirectory) {
              const count = countNotes(node)
              const isExp = effectiveExpanded.has(node.path)
              return (
                <div
                  key={node.path}
                  role="treeitem"
                  aria-expanded={isExp}
                  className={cn(
                    'flex items-center gap-1 px-2 cursor-pointer text-sm',
                    'min-h-[28px] mx-1 rounded-sm',
                    'hover:bg-accent transition-colors',
                  )}
                  style={{ paddingLeft: `${depth * 16 + 8}px` }}
                  onClick={() => toggleFolder(node.path)}
                >
                  {isExp
                    ? <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
                    : <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />}
                  <Folder className="h-4 w-4 shrink-0 text-muted-foreground" />
                  <span className="truncate flex-1">{node.name}</span>
                  <span className="text-[10px] text-muted-foreground/50 tabular-nums shrink-0">{count}</span>
                </div>
              )
            }

            return (
              <div
                key={node.path}
                role="treeitem"
                aria-selected={selectedFile === node.path}
                className={cn(
                  'group flex items-center gap-1 px-2 cursor-pointer text-sm',
                  'min-h-[28px] mx-1 rounded-sm',
                  'hover:bg-accent transition-colors',
                  selectedFile === node.path && 'bg-accent text-accent-foreground',
                )}
                style={{ paddingLeft: `${depth * 16 + 8}px` }}
                onClick={() => onFileSelect(node.path)}
              >
                <span className="h-4 w-4" />
                <PenLine className={cn(
                  'h-4 w-4 shrink-0',
                  selectedFile === node.path ? 'text-teal-400' : 'text-muted-foreground',
                )} />
                <span className="truncate flex-1">{node.name.replace(/\.md$/, '')}</span>
                <button
                  onClick={e => handleDelete(node.path, e)}
                  className={cn(
                    'flex items-center justify-center h-5 w-5 rounded-sm shrink-0 transition-all',
                    deleteTarget === node.path
                      ? 'opacity-100 text-rose-400 hover:bg-rose-500/15'
                      : 'opacity-0 group-hover:opacity-60 text-muted-foreground hover:text-foreground hover:bg-accent',
                  )}
                  title={deleteTarget === node.path ? 'Click again to delete' : 'Delete note'}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            )
          })}

          {/* Empty state */}
          {tree.length === 0 && !isCreating && (
            <button
              onClick={startCreate}
              className={cn(
                'flex items-center gap-1 px-2 w-full text-left text-sm',
                'min-h-[28px] mx-1 rounded-sm',
                'text-muted-foreground/30 hover:text-muted-foreground/60 hover:bg-accent/30 transition-colors',
              )}
              style={{ paddingLeft: '8px' }}
            >
              <span className="h-4 w-4" />
              <PenLine className="h-4 w-4 shrink-0" />
              <span>New note…</span>
            </button>
          )}
        </div>
      )}
    </div>
  )
}
