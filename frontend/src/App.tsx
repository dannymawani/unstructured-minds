import { useState, useCallback, useMemo, useRef, useEffect, lazy, Suspense } from 'react'
import { Routes, Route, Navigate, useNavigate, useLocation, useSearchParams } from 'react-router'
import { Button } from '@/components/ui/button'
import { FileTree } from '@/components/FileTree'
import { MarkdownEditor } from '@/components/Editor/MarkdownEditor'
import { ChatPanel } from '@/components/Chat'
import { SettingsPanel } from '@/components/Settings'
import { CommandPalette, createDefaultCommands } from '@/components/CommandPalette'
import { SearchModal } from '@/components/Search'
import { TemplatePicker } from '@/components/TemplatePicker'
import { QuickCapture } from '@/components/QuickCapture'
import { DailyNoteWizard } from '@/components/DailyNoteWizard'
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
  User,
  Sun,
  Moon,
  Settings,
  Search,
  Hash,
  Link2,
  Loader2,
  Menu,
  MessageSquare,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'

// Lazy load heavy view components for code splitting
const Dashboard = lazy(() => import('@/components/Dashboard/Dashboard').then(m => ({ default: m.Dashboard })))
const KanbanBoard = lazy(() => import('@/components/Kanban/KanbanBoard').then(m => ({ default: m.KanbanBoard })))
const CalendarView = lazy(() => import('@/components/Calendar/CalendarView').then(m => ({ default: m.CalendarView })))
const LifeProfile = lazy(() => import('@/components/LifeProfile/LifeProfile').then(m => ({ default: m.LifeProfile })))

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

type View = 'editor' | 'dashboard' | 'kanban' | 'calendar' | 'profile'
type SidebarTab = 'files' | 'tags' | 'links'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function App() {
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams] = useSearchParams()

  // Derive view from URL pathname instead of state
  const view: View = useMemo(() => {
    const path = location.pathname.replace(/^\//, '')
    if (path === 'dashboard') return 'dashboard'
    if (path === 'kanban') return 'kanban'
    if (path === 'calendar') return 'calendar'
    if (path === 'profile') return 'profile'
    return 'editor'
  }, [location.pathname])

  const [selectedFile, setSelectedFile] = useState<string | undefined>()
  const [content, setContent] = useState('')
  const contentRef = useRef(content)
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
  const [isChatExpanded, setIsChatExpanded] = useState(false)
  const [chatInitialMessage, setChatInitialMessage] = useState<string | undefined>()
  const [isWizardOpen, setIsWizardOpen] = useState(false)
  const [wizardDate, setWizardDate] = useState('')
  const [wizardNoteContent, setWizardNoteContent] = useState('')
  const [wizardNotePath, setWizardNotePath] = useState('')

  const fetchFileContent = useCallback(async (path: string) => {
    try {
      const response = await fetch(
        `${API_BASE_URL}/vault/file?path=${encodeURIComponent(path)}`
      )
      if (!response.ok) {
        throw new Error('Failed to fetch file')
      }
      const data = await response.json()
      return data.content as string
    } catch (err) {
      console.error('Error loading file:', err)
      return ''
    }
  }, [])

  const handleFileSelect = useCallback(
    async (path: string) => {
      // Fetch content FIRST, then update selectedFile so the editor
      // remounts (via key={selectedFile}) with the correct content
      const fileContent = await fetchFileContent(path)
      setContent(fileContent)
      setSelectedFile(path)
      navigate(`/editor?file=${encodeURIComponent(path)}`)
      // Close mobile sidebar after selection
      if (isMobile || isTablet) {
        setIsMobileSidebarOpen(false)
      }
    },
    [fetchFileContent, isMobile, isTablet, navigate]
  )

  const handleContentChange = useCallback((markdown: string) => {
    setContent(markdown)
    contentRef.current = markdown
    isDirtyRef.current = true
  }, [])

  // Called by ChatPanel when note-assist returns updated content
  const handleNoteContentUpdate = useCallback((newContent: string) => {
    setContent(newContent)
    contentRef.current = newContent
    isDirtyRef.current = true

    // Save to disk immediately so content isn't lost on refresh
    if (selectedFile) {
      fetch(`${API_BASE_URL}/vault/file?extract=false`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: selectedFile, content: newContent }),
      }).then(() => {
        isDirtyRef.current = false
      }).catch((err) => console.error('Error saving note-assist update:', err))
    }
  }, [selectedFile])

  // Autosave: disk only, no extraction (called by 60s interval)
  const handleAutosave = useCallback(async () => {
    if (!selectedFile) return

    setSaveState('saving')
    try {
      const response = await fetch(`${API_BASE_URL}/vault/file?extract=false`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: selectedFile, content: contentRef.current }),
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
  }, [selectedFile])

  // Explicit save: disk + extraction (Cmd+S)
  const handleSave = useCallback(async () => {
    if (!selectedFile) return

    setSaveState('extracting')
    try {
      const response = await fetch(`${API_BASE_URL}/vault/file?extract=true`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: selectedFile, content: contentRef.current }),
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
  }, [selectedFile])

  // Extract on file switch if content is dirty
  const prevFileRef = useRef<string | undefined>(selectedFile)
  useEffect(() => {
    if (prevFileRef.current && prevFileRef.current !== selectedFile && isDirtyRef.current) {
      // Fire save+extract for the file we're leaving
      const prevFile = prevFileRef.current
      fetch(`${API_BASE_URL}/vault/file?extract=true`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: prevFile, content: contentRef.current }),
      }).catch((err) => console.error('Error saving on file switch:', err))
      isDirtyRef.current = false
    }
    prevFileRef.current = selectedFile
  }, [selectedFile])

  // Deep link: load file from ?file= query param (supports browser back/forward)
  const fileParam = searchParams.get('file')
  useEffect(() => {
    if (fileParam && fileParam !== selectedFile) {
      fetchFileContent(fileParam).then((fileContent) => {
        setContent(fileContent)
        contentRef.current = fileContent
        isDirtyRef.current = false
        setSelectedFile(fileParam)
      })
    }
  }, [fileParam, selectedFile, fetchFileContent])

  // Handle file deletion — clear editor if deleted file was open
  const handleDeleteFile = useCallback(
    (path: string) => {
      if (selectedFile === path) {
        setSelectedFile(undefined)
        setContent('')
        contentRef.current = ''
        isDirtyRef.current = false
        navigate('/editor')
      }
    },
    [selectedFile, navigate]
  )

  // Toggle sidebar visibility
  const toggleSidebar = useCallback(() => {
    if (isMobile || isTablet) {
      setIsMobileSidebarOpen((prev) => !prev)
    } else {
      setIsSidebarVisible((prev) => !prev)
    }
  }, [isMobile, isTablet])

  // Handle wizard completion — populate note, save with extraction
  const handleWizardComplete = useCallback(async (populatedContent: string) => {
    setIsWizardOpen(false)
    setContent(populatedContent)
    contentRef.current = populatedContent
    setSelectedFile(wizardNotePath)
    navigate(`/editor?file=${encodeURIComponent(wizardNotePath)}`)

    // Save with extraction
    try {
      await fetch(`${API_BASE_URL}/vault/file?extract=true`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: wizardNotePath, content: populatedContent }),
      })
      isDirtyRef.current = false
    } catch (err) {
      console.error('Error saving wizard-populated note:', err)
    }
  }, [wizardNotePath, navigate])

  // Create or open today's daily note
  const createDailyNote = useCallback(async () => {
    const today = new Date()
    const year = today.getFullYear()
    const month = String(today.getMonth() + 1).padStart(2, '0')
    const day = String(today.getDate()).padStart(2, '0')
    const dateStr = `${year}-${month}-${day}`
    const dailyNotePath = `Daily-Notes/${year}-${month}/${dateStr}.md`

    let isNewNote = false
    try {
      const res = await fetch(`${API_BASE_URL}/calendar/daily-note`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ date: dateStr }),
      })
      if (res.ok) {
        const data = await res.json()
        isNewNote = data.created
      }
    } catch (err) {
      console.error('Error creating daily note:', err)
    }

    // Fetch content
    const fileContent = await fetchFileContent(dailyNotePath)

    if (isNewNote) {
      // Open wizard for new notes
      setWizardDate(dateStr)
      setWizardNoteContent(fileContent)
      setWizardNotePath(dailyNotePath)
      setIsWizardOpen(true)
    } else {
      // Existing note — open directly
      setContent(fileContent)
      navigate(`/editor?file=${encodeURIComponent(dailyNotePath)}`)
      setSelectedFile(dailyNotePath)
    }
  }, [fetchFileContent, navigate])

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
    async (path: string) => {
      const fileContent = await fetchFileContent(path)
      setContent(fileContent)
      setSelectedFile(path)
      navigate(`/editor?file=${encodeURIComponent(path)}`)
    },
    [fetchFileContent, navigate]
  )

  // Handle template creation result
  const handleTemplateSelect = useCallback(
    async (path: string) => {
      const fileContent = await fetchFileContent(path)
      setContent(fileContent)
      setSelectedFile(path)
      navigate(`/editor?file=${encodeURIComponent(path)}`)
    },
    [fetchFileContent, navigate]
  )

  // Handle calendar day selection
  const handleCalendarDaySelect = useCallback(
    async (date: string, hasNote: boolean) => {
      const [year, month] = date.split('-')
      const dailyNotePath = `Daily-Notes/${year}-${month}/${date}.md`

      if (!hasNote) {
        // Create new note via API first
        try {
          await fetch(`${API_BASE_URL}/calendar/daily-note`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ date }),
          })
        } catch (err) {
          console.error('Error creating daily note:', err)
        }
      }

      // Fetch content
      const fileContent = await fetchFileContent(dailyNotePath)

      if (!hasNote) {
        // Open wizard for new notes
        setWizardDate(date)
        setWizardNoteContent(fileContent)
        setWizardNotePath(dailyNotePath)
        setIsWizardOpen(true)
      } else {
        // Existing note — open directly
        setContent(fileContent)
        setSelectedFile(dailyNotePath)
        navigate(`/editor?file=${encodeURIComponent(dailyNotePath)}`)
      }
    },
    [fetchFileContent, navigate]
  )

  // Command palette commands
  const commands = useMemo(
    () =>
      createDefaultCommands({
        onSave: handleSave,
        onToggleSidebar: toggleSidebar,
        onCreateDailyNote: createDailyNote,
        onOpenCommandPalette: openCommandPalette,
        onSwitchToEditor: () => navigate('/editor'),
        onSwitchToDashboard: () => navigate('/dashboard'),
        onSwitchToKanban: () => navigate('/kanban'),
        onSwitchToCalendar: () => navigate('/calendar'),
        onSwitchToProfile: () => navigate('/profile'),
        onSearch: openSearch,
        onNewFromTemplate: openTemplatePicker,
        onQuickCapture: openQuickCapture,
      }),
    [handleSave, toggleSidebar, createDailyNote, openCommandPalette, navigate, openSearch, openTemplatePicker, openQuickCapture]
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
      <div className="flex border-b border-border/50">
        <button
          className={`flex-1 flex items-center justify-center gap-1 px-2 py-1.5 sm:py-1 text-xs font-medium transition-colors min-h-[44px] sm:min-h-0 ${
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
          className={`flex-1 flex items-center justify-center gap-1 px-2 py-1.5 sm:py-1 text-xs font-medium transition-colors min-h-[44px] sm:min-h-0 ${
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
          className={`flex-1 flex items-center justify-center gap-1 px-2 py-1.5 sm:py-1 text-xs font-medium transition-colors min-h-[44px] sm:min-h-0 ${
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
            onDeleteFile={handleDeleteFile}
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

  // Editor view element (used by both / and /editor routes)
  const editorElement = (
    <>
      {/* Desktop Sidebar */}
      {!isMobile && !isTablet && isSidebarVisible && (
        <aside className="w-64 bg-card border-r border-border/50 flex flex-col overflow-hidden">
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

      {/* Editor + Chat below */}
      <section className="flex-1 flex flex-col min-h-0 overflow-hidden">
        {selectedFile ? (
          <div className="flex-1 overflow-auto p-3 sm:p-6">
            <MarkdownEditor
              key={selectedFile}
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

        {/* Desktop Chat panel — below editor, collapsible */}
        {!isMobile && !isTablet && (
          <>
            <button
              onClick={() => setIsChatExpanded(prev => !prev)}
              className="flex items-center justify-center gap-2 px-3 py-2 border-t border-border/50 text-xs text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors"
            >
              <MessageSquare className="h-3.5 w-3.5" />
              <span>{isChatExpanded ? 'Hide Chat' : 'Chat'}</span>
              {isChatExpanded
                ? <ChevronDown className="h-3.5 w-3.5" />
                : <ChevronUp className="h-3.5 w-3.5" />
              }
            </button>
            {isChatExpanded && (
              <div className="h-96 border-t border-border/50 flex flex-col overflow-hidden">
                <ChatPanel
                  apiBaseUrl={API_BASE_URL}
                  currentFile={selectedFile}
                  currentContent={content}
                  onContentUpdate={handleNoteContentUpdate}
                  initialMessage={chatInitialMessage}
                />
              </div>
            )}
          </>
        )}
      </section>

      {/* Mobile/Tablet Chat Drawer */}
      {(isMobile || isTablet) && (
        <Drawer
          isOpen={isMobileChatOpen}
          onClose={() => setIsMobileChatOpen(false)}
          position={isMobile ? 'bottom' : 'right'}
          title="Chat"
        >
          <ChatPanel
            apiBaseUrl={API_BASE_URL}
            currentFile={selectedFile}
            currentContent={content}
            onContentUpdate={handleNoteContentUpdate}
            initialMessage={chatInitialMessage}
          />
        </Drawer>
      )}
    </>
  )

  return (
    <div className={`h-screen flex flex-col overflow-hidden ${isMobile ? 'pb-16' : ''}`}>
      {/* Header */}
      <header className="bg-card border-b border-border/50 px-4 sm:px-6 py-3 sm:py-4 flex items-center justify-between shadow-sm">
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

          <h1 className="text-sm sm:text-base font-semibold tracking-tight truncate">
            {isMobile ? 'UM' : 'Unstructured Minds'}
          </h1>

          {/* Desktop navigation tabs */}
          {!isMobile && (
            <div className="hidden sm:flex items-center gap-1 bg-muted rounded-lg p-1">
              <Button
                variant={view === 'editor' ? 'secondary' : 'ghost'}
                size="sm"
                onClick={() => navigate('/editor')}
                className="gap-1"
              >
                <FileText className="w-4 h-4" />
                <span className="hidden lg:inline">Editor</span>
              </Button>
              <Button
                variant={view === 'dashboard' ? 'secondary' : 'ghost'}
                size="sm"
                onClick={() => navigate('/dashboard')}
                className="gap-1"
              >
                <LayoutDashboard className="w-4 h-4" />
                <span className="hidden lg:inline">Dashboard</span>
              </Button>
              <Button
                variant={view === 'kanban' ? 'secondary' : 'ghost'}
                size="sm"
                onClick={() => navigate('/kanban')}
                className="gap-1"
              >
                <Kanban className="w-4 h-4" />
                <span className="hidden lg:inline">Kanban</span>
              </Button>
              <Button
                variant={view === 'calendar' ? 'secondary' : 'ghost'}
                size="sm"
                onClick={() => navigate('/calendar')}
                className="gap-1"
              >
                <Calendar className="w-4 h-4" />
                <span className="hidden lg:inline">Calendar</span>
              </Button>
              <Button
                variant={view === 'profile' ? 'secondary' : 'ghost'}
                size="sm"
                onClick={() => navigate('/profile')}
                className="gap-1"
              >
                <User className="w-4 h-4" />
                <span className="hidden lg:inline">Profile</span>
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
            className="min-w-[44px] min-h-[44px] sm:min-w-0 sm:min-h-0 p-0 sm:p-2"
          >
            <Search className="w-4 h-4 sm:w-4 sm:h-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={toggleTheme}
            aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
            className="min-w-[44px] min-h-[44px] sm:min-w-0 sm:min-h-0 p-0 sm:p-2"
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
            className="gap-1 min-h-[44px] sm:min-h-0 sm:h-8"
          >
            <Settings className="w-4 h-4" />
            <span className="hidden sm:inline">Settings</span>
          </Button>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 flex overflow-hidden">
        <Routes>
          <Route path="/dashboard" element={
            <Suspense fallback={<ViewLoadingFallback />}>
              <section className="flex-1 overflow-auto bg-background">
                <Dashboard apiUrl={API_BASE_URL} />
              </section>
            </Suspense>
          } />
          <Route path="/kanban" element={
            <Suspense fallback={<ViewLoadingFallback />}>
              <section className="flex-1 overflow-auto bg-background">
                <KanbanBoard apiUrl={API_BASE_URL} onFileSelect={handleFileSelect} />
              </section>
            </Suspense>
          } />
          <Route path="/calendar" element={
            <Suspense fallback={<ViewLoadingFallback />}>
              <section className="flex-1 overflow-auto bg-background">
                <CalendarView
                  apiUrl={API_BASE_URL}
                  onDaySelect={handleCalendarDaySelect}
                />
              </section>
            </Suspense>
          } />
          <Route path="/profile" element={
            <Suspense fallback={<ViewLoadingFallback />}>
              <section className="flex-1 overflow-auto bg-background">
                <LifeProfile apiUrl={API_BASE_URL} />
              </section>
            </Suspense>
          } />
          <Route path="/editor" element={editorElement} />
          <Route path="/" element={editorElement} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>

      {/* Mobile bottom navigation */}
      {isMobile && <MobileNav currentView={view} onViewChange={(v) => navigate(v === 'editor' ? '/editor' : `/${v}`)} />}

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

      {/* Daily Note Wizard */}
      <DailyNoteWizard
        isOpen={isWizardOpen}
        onClose={() => setIsWizardOpen(false)}
        onComplete={handleWizardComplete}
        noteContent={wizardNoteContent}
        date={wizardDate}
      />
    </div>
  )
}

export default App
