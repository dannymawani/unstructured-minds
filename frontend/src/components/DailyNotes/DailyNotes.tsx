import { useState, useEffect, useCallback, useMemo } from 'react'
import { ChevronRight, ChevronDown, Folder, FileText, CalendarPlus } from 'lucide-react'
import { cn } from '@/lib/utils'
import { api } from '@/lib/apiClient'
import { buildTree, flattenTree, type FileNode } from '@/components/FileTree'

const YEAR_PATTERN = /^\d{4}$/
const MONTH_PATTERN = /^\d{2}$/
const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

interface DailyNotesProps {
  onFileSelect: (path: string) => void
  selectedFile?: string
  refreshTrigger?: number
  onCreateDailyNote?: () => void
}

function loadSectionExpanded(): boolean {
  try {
    const v = localStorage.getItem('daily-notes-section-expanded')
    return v !== null ? v === 'true' : true
  } catch { return true }
}

function loadFolderExpanded(): Set<string> {
  try {
    const v = localStorage.getItem('daily-notes-folders-expanded')
    if (v) return new Set(JSON.parse(v))
  } catch { /* use defaults */ }
  const now = new Date()
  const year = String(now.getFullYear())
  const month = String(now.getMonth() + 1).padStart(2, '0')
  return new Set([year, `${year}/${month}`])
}

function addMonthDisplayNames(nodes: FileNode[]): FileNode[] {
  return nodes.map(node => {
    if (node.isDirectory && MONTH_PATTERN.test(node.name)) {
      const monthIdx = parseInt(node.name, 10) - 1
      return {
        ...node,
        displayName: MONTH_NAMES[monthIdx] || node.name,
        children: node.children
          ? [...node.children].sort((a, b) => b.name.localeCompare(a.name))
          : [],
      }
    }
    return node
  })
}


export function DailyNotes({ onFileSelect, selectedFile, refreshTrigger, onCreateDailyNote }: DailyNotesProps) {
  const [sectionExpanded, setSectionExpanded] = useState(loadSectionExpanded)
  const [expanded, setExpanded] = useState(loadFolderExpanded)
  const [tree, setTree] = useState<FileNode[]>([])

  useEffect(() => {
    localStorage.setItem('daily-notes-section-expanded', String(sectionExpanded))
  }, [sectionExpanded])

  useEffect(() => {
    localStorage.setItem('daily-notes-folders-expanded', JSON.stringify([...expanded]))
  }, [expanded])

  const fetchNotes = useCallback(async () => {
    try {
      const data = await api.get<{ files: Array<{ path: string; name: string; is_directory: boolean }> }>('/vault/files')
      const fullTree = buildTree(data.files)
      const yearNodes = fullTree
        .filter(n => n.isDirectory && YEAR_PATTERN.test(n.name))
        .sort((a, b) => b.name.localeCompare(a.name))
        .map(yearNode => ({
          ...yearNode,
          children: addMonthDisplayNames(
            (yearNode.children || []).sort((a, b) => b.name.localeCompare(a.name))
          ),
        }))
      setTree(yearNodes)
    } catch { /* silently fail */ }
  }, [])

  useEffect(() => { fetchNotes() }, [fetchNotes, refreshTrigger])

  const flattened = useMemo(
    () => flattenTree(tree, expanded),
    [tree, expanded]
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

  return (
    <div className="flex flex-col min-h-0" role="tree" aria-label="Daily notes">
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
            Daily Notes
          </span>
        </button>
        <div className="flex-1 h-px bg-border/30" />
        {sectionExpanded && onCreateDailyNote && (
          <button
            onClick={onCreateDailyNote}
            className="flex items-center justify-center h-5 w-5 rounded-sm text-muted-foreground/40 hover:text-foreground hover:bg-accent/60 transition-colors"
            title="Create today's note"
          >
            <CalendarPlus className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      {sectionExpanded && (
        <div className="overflow-auto min-h-0 pb-2">
          {flattened.map(({ node, depth }) => {
            if (node.isDirectory) {
              const isExp = expanded.has(node.path)
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
                  <span className="truncate flex-1">{node.displayName || node.name}</span>
                </div>
              )
            }

            return (
              <div
                key={node.path}
                role="treeitem"
                aria-selected={selectedFile === node.path}
                className={cn(
                  'flex items-center gap-1 px-2 cursor-pointer text-sm',
                  'min-h-[28px] mx-1 rounded-sm',
                  'hover:bg-accent transition-colors',
                  selectedFile === node.path && 'bg-accent text-accent-foreground',
                )}
                style={{ paddingLeft: `${depth * 16 + 8}px` }}
                onClick={() => onFileSelect(node.path)}
              >
                <span className="h-4 w-4" />
                <FileText className={cn(
                  'h-4 w-4 shrink-0',
                  selectedFile === node.path ? 'text-teal-400' : 'text-muted-foreground',
                )} />
                <span className="truncate flex-1">{node.name.replace(/\.md$/, '').replace(/-daily-note$/, '')}</span>
              </div>
            )
          })}

          {tree.length === 0 && (
            <div className="px-4 py-2 text-sm text-muted-foreground/30">
              No daily notes yet
            </div>
          )}
        </div>
      )}
    </div>
  )
}
