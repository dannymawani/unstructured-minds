import { useState, useEffect, useRef, useCallback } from 'react'
import { cn } from '@/lib/utils'
import {
  Save,
  Command,
  PanelLeftClose,
  CalendarDays,
  Calendar,
  FileText,
  LayoutDashboard,
  Kanban,
  Search,
  FilePlus2,
  Zap,
  type LucideIcon,
} from 'lucide-react'

export interface CommandItem {
  id: string
  label: string
  shortcut?: string
  icon?: LucideIcon
  action: () => void
}

interface CommandPaletteProps {
  isOpen: boolean
  onClose: () => void
  commands: CommandItem[]
}

export function CommandPalette({ isOpen, onClose, commands }: CommandPaletteProps) {
  const [search, setSearch] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLDivElement>(null)

  const filteredCommands = commands.filter((cmd) =>
    cmd.label.toLowerCase().includes(search.toLowerCase())
  )

  // Reset state when opening
  useEffect(() => {
    if (isOpen) {
      setSearch('')
      setSelectedIndex(0)
      // Focus input after a short delay to ensure modal is rendered
      setTimeout(() => inputRef.current?.focus(), 10)
    }
  }, [isOpen])

  // Keyboard navigation
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault()
          setSelectedIndex((prev) =>
            prev < filteredCommands.length - 1 ? prev + 1 : 0
          )
          break
        case 'ArrowUp':
          e.preventDefault()
          setSelectedIndex((prev) =>
            prev > 0 ? prev - 1 : filteredCommands.length - 1
          )
          break
        case 'Enter':
          e.preventDefault()
          if (filteredCommands[selectedIndex]) {
            filteredCommands[selectedIndex].action()
            onClose()
          }
          break
        case 'Escape':
          e.preventDefault()
          onClose()
          break
      }
    },
    [filteredCommands, selectedIndex, onClose]
  )

  // Scroll selected item into view
  useEffect(() => {
    if (listRef.current) {
      const selectedElement = listRef.current.children[selectedIndex] as HTMLElement
      if (selectedElement) {
        selectedElement.scrollIntoView({ block: 'nearest' })
      }
    }
  }, [selectedIndex])

  // Reset selection when search changes
  useEffect(() => {
    setSelectedIndex(0)
  }, [search])

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh]"
      onClick={onClose}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" />

      {/* Modal */}
      <div
        className={cn(
          'relative w-full max-w-lg rounded-lg border bg-background shadow-lg',
          'animate-in fade-in-0 zoom-in-95 duration-150'
        )}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search input */}
        <div className="flex items-center border-b px-3">
          <Command className="h-4 w-4 text-muted-foreground" />
          <input
            ref={inputRef}
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a command..."
            className={cn(
              'flex-1 bg-transparent px-3 py-3 text-sm',
              'focus:outline-none placeholder:text-muted-foreground'
            )}
          />
        </div>

        {/* Command list */}
        <div ref={listRef} className="max-h-[300px] overflow-auto p-2">
          {filteredCommands.length === 0 ? (
            <div className="py-6 text-center text-sm text-muted-foreground">
              No commands found.
            </div>
          ) : (
            filteredCommands.map((cmd, index) => {
              const Icon = cmd.icon
              return (
                <button
                  key={cmd.id}
                  className={cn(
                    'flex w-full items-center justify-between rounded-md px-3 py-2 text-sm',
                    'hover:bg-accent',
                    index === selectedIndex && 'bg-accent'
                  )}
                  onClick={() => {
                    cmd.action()
                    onClose()
                  }}
                  onMouseEnter={() => setSelectedIndex(index)}
                >
                  <div className="flex items-center gap-3">
                    {Icon && <Icon className="h-4 w-4 text-muted-foreground" />}
                    <span>{cmd.label}</span>
                  </div>
                  {cmd.shortcut && (
                    <kbd className="rounded bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                      {cmd.shortcut}
                    </kbd>
                  )}
                </button>
              )
            })
          )}
        </div>
      </div>
    </div>
  )
}

// Default commands factory - creates standard app commands
export function createDefaultCommands(options: {
  onSave: () => void
  onToggleSidebar: () => void
  onCreateDailyNote: () => void
  onOpenCommandPalette: () => void
  onSwitchToEditor: () => void
  onSwitchToDashboard: () => void
  onSwitchToKanban: () => void
  onSwitchToCalendar?: () => void
  onSearch?: () => void
  onNewFromTemplate?: () => void
  onQuickCapture?: () => void
}): CommandItem[] {
  const commands: CommandItem[] = [
    {
      id: 'save',
      label: 'Save file',
      shortcut: 'Cmd+S',
      icon: Save,
      action: options.onSave,
    },
    {
      id: 'command-palette',
      label: 'Command palette',
      shortcut: 'Cmd+K',
      icon: Command,
      action: options.onOpenCommandPalette,
    },
    {
      id: 'toggle-sidebar',
      label: 'Toggle sidebar',
      shortcut: 'Cmd+B',
      icon: PanelLeftClose,
      action: options.onToggleSidebar,
    },
    {
      id: 'daily-note',
      label: 'Create/open daily note',
      shortcut: 'Cmd+D',
      icon: CalendarDays,
      action: options.onCreateDailyNote,
    },
    {
      id: 'view-editor',
      label: 'Switch to Editor view',
      icon: FileText,
      action: options.onSwitchToEditor,
    },
    {
      id: 'view-dashboard',
      label: 'Switch to Dashboard view',
      icon: LayoutDashboard,
      action: options.onSwitchToDashboard,
    },
    {
      id: 'view-kanban',
      label: 'Switch to Kanban view',
      icon: Kanban,
      action: options.onSwitchToKanban,
    },
  ]

  if (options.onSwitchToCalendar) {
    commands.push({
      id: 'view-calendar',
      label: 'Switch to Calendar view',
      icon: Calendar,
      action: options.onSwitchToCalendar,
    })
  }

  if (options.onSearch) {
    commands.splice(2, 0, {
      id: 'search',
      label: 'Search notes',
      shortcut: 'Cmd+Shift+F',
      icon: Search,
      action: options.onSearch,
    })
  }

  if (options.onNewFromTemplate) {
    commands.splice(4, 0, {
      id: 'new-from-template',
      label: 'New from template',
      icon: FilePlus2,
      action: options.onNewFromTemplate,
    })
  }

  if (options.onQuickCapture) {
    commands.splice(5, 0, {
      id: 'quick-capture',
      label: 'Quick capture',
      shortcut: 'Cmd+Shift+N',
      icon: Zap,
      action: options.onQuickCapture,
    })
  }

  return commands
}
