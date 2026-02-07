import { useState, useCallback, useMemo, useRef, useEffect, lazy, Suspense } from 'react'
import { Button } from '@/components/ui/button'
import { FileTree } from '@/components/FileTree'
import { MarkdownEditor } from '@/components/Editor/MarkdownEditor'
import { ChatPanel } from '@/components/Chat'
import { SettingsPanel } from '@/components/Settings'
import { CommandPalette, createDefaultCommands } from '@/components/CommandPalette'
import { SearchModal } from '@/components/Search'
import { TemplatePicker } from '@/components/TemplatePicker'
import { QuickCapture } from '@/components/QuickCapture'
import { TagsPanel } from '@/components/TagsPanel'
import { BacklinksPanel } from '@/components/BacklinksPanel'
import { MobileNav } from '@/components/MobileNav'
import { Drawer } from '@/components/Drawer'
import { useKeyboardShortcuts, type KeyboardShortcut } from '@/hooks/useKeyboardShortcuts'
import { useTheme } from '@/hooks/useTheme'
import { useMobile } from '@/hooks/useMobile'
import {
  LayoutDashboard,
  FileText,
  Kanban,
  Calendar,
  Sun,
  Moon,
  Settings,
  Search,
  Hash,
  Link2,
  Loader2,
  Menu,
  MessageSquare,
} from 'lucide-react'

// Lazy load heavy view components for code splitting
const Dashboard = lazy(() => import('@/components/Dashboard/Dashboard').then(m => ({ default: m.Dashboard })))
const KanbanBoard = lazy(() => import('@/components/Kanban/KanbanBoard').then(m => ({ default: m.KanbanBoard })))
const CalendarView = lazy(() => import('@/components/Calendar/CalendarView').then(m => ({ default: m.CalendarView })))

// Loading fallback component
function ViewLoadingFallback() {
  return (
    <div className="flex-1 flex items-center justify-center">
      <div className="flex flex-col items-center gap-3 text-muted-foreground">
        <Loader2 className="w-8 h-8 animate-spin" />
        <p className="text-sm">Loading view...</p>
      </div>
    </div>
  )
}

type View = 'editor' | 'dashboard' | 'kanban' | 'calendar'
type SidebarTab = 'files' | 'tags' | 'links'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function App() {
  const [view, setView] = useState<View>('editor')
  const [selectedFile, setSelectedFile] = useState<string | undefined>()
  const [content, setContent] = useState('')
  const [saveState, setSaveState] = useState<'idle' | 'saving' | 'extracting' | 'saved'>('idle')
  const isDirtyRef = useRef(false)
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false)
  const [isSidebarVisible, setIsSidebarVisible] = useState(true)
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  const [isSearchOpen, setIsSearchOpen] = useState(false)
  const [isTemplatePickerOpen, setIsTemplatePickerOpen] = useState(false)
  const [isQuickCaptureOpen, setIsQuickCaptureOpen] = useState(false)
  const [sidebarTab, setSidebarTab] = useState<SidebarTab>('files')
  const { theme, toggleTheme, setTheme } = useTheme()

  // Mobile state
  const { isMobile, isTablet } = useMobile()
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false)
  const [isMobileChatOpen, setIsMobileChatOpen] = useState(false)

  const fetchFileContent = useCallback(async (path: string) => {
    try {
      const response = await fetch(
        `${API_BASE_URL}/vault/file?path=${encodeURIComponent(path)}`
      )
      if (!response.ok) {
        throw new Error('Failed to fetch file')
      }
      const data = await response.json()
      setContent(data.content)
    } catch (err) {
      console.error('Error loading file:', err)
      setContent('')
    }
  }, [])

  const handleFileSelect = useCallback(
    (path: string) => {
      setSelectedFile(path)
      fetchFileContent(path)
      // Close mobile sidebar after selection
      if (isMobile || isTablet) {
        setIsMobileSidebarOpen(false)
      }
    },
    [fetchFileContent, isMobile, isTablet]
  )

  const handleContentChange = useCallback((markdown: string) => {
    setContent(markdown)
    isDirtyRef.current = true
  }, [])

  // Autosave: disk only, no extraction (called by 60s interval)
  const handleAutosave = useCallback(async () => {
    if (!selectedFile) return

    setSaveState('saving')
    try {
      const response = await fetch(`${API_BASE_URL}/vault/file?extract=false`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: selectedFile, content }),
      })
      if (!response.ok) {
        throw new Error('Failed to save file')
      }
      isDirtyRef.current = false
      setSaveState('saved')
      setTimeout(() => setSaveState('idle'), 2000)
    } catch (err) {
      console.error('Error saving file:', err)
      setSaveState('idle')
    }
  }, [selectedFile, content])

  // Explicit save: disk + extraction (Cmd+S)
  const handleSave = useCallback(async () => {
    if (!selectedFile) return

    setSaveState('extracting')
    try {
      const response = await fetch(`${API_BASE_URL}/vault/file?extract=true`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: selectedFile, content }),
      })
      if (!response.ok) {
        throw new Error('Failed to save file')
      }
      isDirtyRef.current = false
      setSaveState('saved')
      setTimeout(() => setSaveState('idle'), 2000)
    } catch (err) {
      console.error('Error saving file:', err)
      setSaveState('idle')
    }
  }, [selectedFile, content])

  // Extract on file switch if content is dirty
  const prevFileRef = useRef<string | undefined>(selectedFile)
  useEffect(() => {
    if (prevFileRef.current && prevFileRef.current !== selectedFile && isDirtyRef.current) {
      // Fire save+extract for the file we're leaving
      const prevFile = prevFileRef.current
      fetch(`${API_BASE_URL}/vault/file?extract=true`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: prevFile, content }),
      }).catch((err) => console.error('Error saving on file switch:', err))
      isDirtyRef.current = false
    }
    prevFileRef.current = selectedFile
  }, [selectedFile, content])

  // Toggle sidebar visibility
  const toggleSidebar = useCallback(() => {
    if (isMobile || isTablet) {
      setIsMobileSidebarOpen((prev) => !prev)
    } else {
      setIsSidebarVisible((prev) => !prev)
    }
  }, [isMobile, isTablet])

  // Create or open today's daily note
  const createDailyNote = useCallback(async () => {
    const today = new Date()
    const year = today.getFullYear()
    const month = String(today.getMonth() + 1).padStart(2, '0')
    const day = String(today.getDate()).padStart(2, '0')
    const dailyNotePath = `Daily-Notes/${year}-${month}/${year}-${month}-${day}.md`

    try {
      // Try to create the daily note via API (it will return existing content if file exists)
      const response = await fetch(`${API_BASE_URL}/vault/daily-note`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ date: `${year}-${month}-${day}` }),
      })

      if (response.ok) {
        // Switch to editor view and select the daily note
        setView('editor')
        setSelectedFile(dailyNotePath)
        fetchFileContent(dailyNotePath)
      } else {
        // Fallback: just try to open the file directly
        setView('editor')
        setSelectedFile(dailyNotePath)
        fetchFileContent(dailyNotePath)
      }
    } catch (err) {
      console.error('Error creating daily note:', err)
      // Fallback: try to open the file anyway
      setView('editor')
      setSelectedFile(dailyNotePath)
      fetchFileContent(dailyNotePath)
    }
  }, [fetchFileContent])

  // Open command palette
  const openCommandPalette = useCallback(() => {
    setIsCommandPaletteOpen(true)
  }, [])

  // Open search modal
  const openSearch = useCallback(() => {
    setIsSearchOpen(true)
  }, [])

  // Open template picker
  const openTemplatePicker = useCallback(() => {
    setIsTemplatePickerOpen(true)
  }, [])

  // Open quick capture
  const openQuickCapture = useCallback(() => {
    setIsQuickCaptureOpen(true)
  }, [])

  // Handle search result selection
  const handleSearchSelect = useCallback(
    (path: string) => {
      setView('editor')
      setSelectedFile(path)
      fetchFileContent(path)
    },
    [fetchFileContent]
  )

  // Handle template creation result
  const handleTemplateSelect = useCallback(
    (path: string) => {
      setView('editor')
      setSelectedFile(path)
      fetchFileContent(path)
    },
    [fetchFileContent]
  )

  // Handle calendar day selection
  const handleCalendarDaySelect = useCallback(
    async (date: string, hasNote: boolean) => {
      const [year, month] = date.split('-')
      const dailyNotePath = `Daily-Notes/${year}-${month}/${date}.md`

      if (hasNote) {
        // Open existing note
        setView('editor')
        setSelectedFile(dailyNotePath)
        fetchFileContent(dailyNotePath)
      } else {
        // Create new note via API
        try {
          const response = await fetch(`${API_BASE_URL}/calendar/daily-note`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ date }),
          })

          if (response.ok) {
            setView('editor')
            setSelectedFile(dailyNotePath)
            fetchFileContent(dailyNotePath)
          }
        } catch (err) {
          console.error('Error creating daily note:', err)
        }
      }
    },
    [fetchFileContent]
  )

  // Command palette commands
  const commands = useMemo(
    () =>
      createDefaultCommands({
        onSave: handleSave,
        onToggleSidebar: toggleSidebar,
        onCreateDailyNote: createDailyNote,
        onOpenCommandPalette: openCommandPalette,
        onSwitchToEditor: () => setView('editor'),
        onSwitchToDashboard: () => setView('dashboard'),
        onSwitchToKanban: () => setView('kanban'),
        onSwitchToCalendar: () => setView('calendar'),
        onSearch: openSearch,
        onNewFromTemplate: openTemplatePicker,
        onQuickCapture: openQuickCapture,
      }),
    [handleSave, toggleSidebar, createDailyNote, openCommandPalette, openSearch, openTemplatePicker, openQuickCapture]
  )

  // Keyboard shortcuts
  const shortcuts: KeyboardShortcut[] = useMemo(
    () => [
      {
        key: 's',
        meta: true,
        action: handleSave,
        description: 'Save current file',
      },
      {
        key: 'k',
        meta: true,
        action: openCommandPalette,
        description: 'Open command palette',
      },
      {
        key: 'b',
        meta: true,
        action: toggleSidebar,
        description: 'Toggle sidebar',
      },
      {
        key: 'd',
        meta: true,
        action: createDailyNote,
        description: 'Create/open daily note',
      },
      {
        key: 'f',
        meta: true,
        shift: true,
        action: openSearch,
        description: 'Search notes',
      },
      {
        key: 'n',
        meta: true,
        shift: true,
        action: openQuickCapture,
        description: 'Quick capture',
      },
      {
        key: 't',
        meta: true,
        action: openTemplatePicker,
        description: 'New note from template',
      },
    ],
    [handleSave, openCommandPalette, toggleSidebar, createDailyNote, openSearch, openQuickCapture, openTemplatePicker]
  )

  // Register keyboard shortcuts
  useKeyboardShortcuts(shortcuts)

  // Sidebar content (shared between desktop and mobile drawer)
  const sidebarContent = (
    <div className="flex flex-col h-full">
      {/* Sidebar tab buttons */}
      <div className="flex border-b">
        <button
          className={`flex-1 flex items-center justify-center gap-1 px-2 py-2 text-xs font-medium transition-colors min-h-[44px] ${
            sidebarTab === 'files'
              ? 'bg-accent text-accent-foreground border-b-2 border-primary'
              : 'text-muted-foreground hover:text-foreground hover:bg-accent/50'
          }`}
          onClick={() => setSidebarTab('files')}
          title="Files"
        >
          <FileText className="h-4 w-4" />
          Files
        </button>
        <button
          className={`flex-1 flex items-center justify-center gap-1 px-2 py-2 text-xs font-medium transition-colors min-h-[44px] ${
            sidebarTab === 'tags'
              ? 'bg-accent text-accent-foreground border-b-2 border-primary'
              : 'text-muted-foreground hover:text-foreground hover:bg-accent/50'
          }`}
          onClick={() => setSidebarTab('tags')}
          title="Tags"
        >
          <Hash className="h-4 w-4" />
          Tags
        </button>
        <button
          className={`flex-1 flex items-center justify-center gap-1 px-2 py-2 text-xs font-medium transition-colors min-h-[44px] ${
            sidebarTab === 'links'
              ? 'bg-accent text-accent-foreground border-b-2 border-primary'
              : 'text-muted-foreground hover:text-foreground hover:bg-accent/50'
          }`}
          onClick={() => setSidebarTab('links')}
          title="Links"
        >
          <Link2 className="h-4 w-4" />
          Links
        </button>
      </div>

      {/* Sidebar content */}
      <div className="flex-1 overflow-hidden">
        {sidebarTab === 'files' && (
          <FileTree
            onFileSelect={handleFileSelect}
            selectedFile={selectedFile}
            apiBaseUrl={API_BASE_URL}
            onCreateDailyNote={createDailyNote}
            onOpenTemplatePicker={openTemplatePicker}
          />
        )}
        {sidebarTab === 'tags' && (
          <TagsPanel
            onFileSelect={handleFileSelect}
            apiBaseUrl={API_BASE_URL}
          />
        )}
        {sidebarTab === 'links' && (
          <BacklinksPanel
            currentFile={selectedFile}
            onFileSelect={handleFileSelect}
            apiBaseUrl={API_BASE_URL}
          />
        )}
      </div>
    </div>
  )

  return (
    <div className={`min-h-screen flex flex-col ${isMobile ? 'pb-16' : ''}`}>
      {/* Header */}
      <header className="border-b px-3 sm:px-4 py-2 sm:py-3 flex items-center justify-between">
        <div className="flex items-center gap-2 sm:gap-4">
          {/* Mobile menu button */}
          {(isMobile || isTablet) && view === 'editor' && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsMobileSidebarOpen(true)}
              className="min-w-[44px] min-h-[44px] p-0"
              aria-label="Open sidebar"
            >
              <Menu className="w-5 h-5" />
            </Button>
          )}

          <h1 className="text-base sm:text-lg font-semibold truncate">
            {isMobile ? 'UM' : 'Unstructured Minds'}
          </h1>

          {/* Desktop navigation tabs */}
          {!isMobile && (
            <div className="hidden sm:flex items-center gap-1 bg-muted rounded-lg p-1">
              <Button
                variant={view === 'editor' ? 'secondary' : 'ghost'}
                size="sm"
                onClick={() => setView('editor')}
                className="gap-1"
              >
                <FileText className="w-4 h-4" />
                <span className="hidden lg:inline">Editor</span>
              </Button>
              <Button
                variant={view === 'dashboard' ? 'secondary' : 'ghost'}
                size="sm"
                onClick={() => setView('dashboard')}
                className="gap-1"
              >
                <LayoutDashboard className="w-4 h-4" />
                <span className="hidden lg:inline">Dashboard</span>
              </Button>
              <Button
                variant={view === 'kanban' ? 'secondary' : 'ghost'}
                size="sm"
                onClick={() => setView('kanban')}
                className="gap-1"
              >
                <Kanban className="w-4 h-4" />
                <span className="hidden lg:inline">Kanban</span>
              </Button>
              <Button
                variant={view === 'calendar' ? 'secondary' : 'ghost'}
                size="sm"
                onClick={() => setView('calendar')}
                className="gap-1"
              >
                <Calendar className="w-4 h-4" />
                <span className="hidden lg:inline">Calendar</span>
              </Button>
            </div>
          )}
        </div>

        <div className="flex items-center gap-1 sm:gap-2">
          {saveState !== 'idle' && (
            <span className="text-xs sm:text-sm text-muted-foreground hidden sm:inline">
              {saveState === 'saving' && 'Saving...'}
              {saveState === 'extracting' && 'Saving & extracting...'}
              {saveState === 'saved' && 'Saved'}
            </span>
          )}

          {/* Mobile chat toggle (only in editor view) */}
          {(isMobile || isTablet) && view === 'editor' && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsMobileChatOpen(true)}
              className="min-w-[44px] min-h-[44px] p-0"
              aria-label="Open chat"
            >
              <MessageSquare className="w-5 h-5" />
            </Button>
          )}

          <Button
            variant="ghost"
            size="sm"
            onClick={openSearch}
            aria-label="Search notes"
            title="Search notes (Cmd+Shift+F)"
            className="min-w-[44px] min-h-[44px] p-0 sm:p-2"
          >
            <Search className="w-4 h-4 sm:w-4 sm:h-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={toggleTheme}
            aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
            className="min-w-[44px] min-h-[44px] p-0 sm:p-2"
          >
            {theme === 'dark' ? (
              <Sun className="w-4 h-4" />
            ) : (
              <Moon className="w-4 h-4" />
            )}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsSettingsOpen(true)}
            className="gap-1 min-h-[44px] sm:min-h-0"
          >
            <Settings className="w-4 h-4" />
            <span className="hidden sm:inline">Settings</span>
          </Button>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 flex overflow-hidden">
        {view === 'editor' ? (
          <>
            {/* Desktop Sidebar */}
            {!isMobile && !isTablet && isSidebarVisible && (
              <aside className="w-64 border-r flex flex-col overflow-hidden">
                {sidebarContent}
              </aside>
            )}

            {/* Mobile/Tablet Sidebar Drawer */}
            {(isMobile || isTablet) && (
              <Drawer
                isOpen={isMobileSidebarOpen}
                onClose={() => setIsMobileSidebarOpen(false)}
                position="left"
                title="Files"
              >
                {sidebarContent}
              </Drawer>
            )}

            {/* Editor */}
            <section className="flex-1 flex flex-col min-h-0 overflow-hidden">
              {selectedFile ? (
                <div className="flex-1 overflow-auto p-2 sm:p-4">
                  <MarkdownEditor
                    content={content}
                    onChange={handleContentChange}
                    onAutosave={handleAutosave}
                  />
                </div>
              ) : (
                <div className="flex items-center justify-center h-full text-muted-foreground p-4 text-center">
                  <p>
                    {isMobile || isTablet
                      ? 'Tap the menu to select a file'
                      : 'Select a file to start editing'}
                  </p>
                </div>
              )}
            </section>

            {/* Desktop Chat panel */}
            {!isMobile && !isTablet && (
              <aside className="w-80 border-l flex flex-col overflow-hidden">
                <ChatPanel apiBaseUrl={API_BASE_URL} />
              </aside>
            )}

            {/* Mobile/Tablet Chat Drawer */}
            {(isMobile || isTablet) && (
              <Drawer
                isOpen={isMobileChatOpen}
                onClose={() => setIsMobileChatOpen(false)}
                position={isMobile ? 'bottom' : 'right'}
                title="Chat"
              >
                <ChatPanel apiBaseUrl={API_BASE_URL} />
              </Drawer>
            )}
          </>
        ) : view === 'dashboard' ? (
          <Suspense fallback={<ViewLoadingFallback />}>
            <section className="flex-1 overflow-auto bg-background">
              <Dashboard apiUrl={API_BASE_URL} />
            </section>
          </Suspense>
        ) : view === 'kanban' ? (
          <Suspense fallback={<ViewLoadingFallback />}>
            <section className="flex-1 overflow-auto bg-background">
              <KanbanBoard apiUrl={API_BASE_URL} />
            </section>
          </Suspense>
        ) : (
          <Suspense fallback={<ViewLoadingFallback />}>
            <section className="flex-1 overflow-auto bg-background">
              <CalendarView
                apiUrl={API_BASE_URL}
                onDaySelect={handleCalendarDaySelect}
              />
            </section>
          </Suspense>
        )}
      </main>

      {/* Mobile bottom navigation */}
      {isMobile && <MobileNav currentView={view} onViewChange={setView} />}

      {/* Command Palette */}
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        commands={commands}
      />

      {/* Settings Panel */}
      <SettingsPanel
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        apiBaseUrl={API_BASE_URL}
        onThemeChange={setTheme}
      />

      {/* Search Modal */}
      <SearchModal
        isOpen={isSearchOpen}
        onClose={() => setIsSearchOpen(false)}
        onSelect={handleSearchSelect}
        apiBaseUrl={API_BASE_URL}
      />

      {/* Template Picker */}
      <TemplatePicker
        isOpen={isTemplatePickerOpen}
        onClose={() => setIsTemplatePickerOpen(false)}
        onSelect={handleTemplateSelect}
        apiBaseUrl={API_BASE_URL}
      />

      {/* Quick Capture */}
      <QuickCapture
        isOpen={isQuickCaptureOpen}
        onClose={() => setIsQuickCaptureOpen(false)}
        apiBaseUrl={API_BASE_URL}
      />
    </div>
  )
}

export default App
