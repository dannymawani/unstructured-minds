import { useState, useEffect, useCallback, useMemo, lazy, Suspense } from 'react'
import { Routes, Route, Navigate, useNavigate, useLocation } from 'react-router'
import { SignedIn, SignedOut, SignInButton, UserButton } from '@clerk/clerk-react'
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
import { useFileManager } from '@/hooks/useFileManager'
import { useUIState } from '@/hooks/useUIState'
import { api, setTokenGetter } from '@/lib/apiClient'
import { useAuth } from '@clerk/clerk-react'
import {
  LayoutDashboard,
  FileText,
  Kanban,
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

const CLERK_ENABLED = !!import.meta.env.VITE_CLERK_PUBLISHABLE_KEY

function SignInGate() {
  return (
    <div className="h-screen flex items-center justify-center bg-background">
      <div className="text-center space-y-6 max-w-sm mx-auto px-4">
        <div className="flex items-center gap-3">
          <img src="/um-logo.svg" alt="Unstructured Minds" className="w-8 h-8" />
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">Unstructured Minds</h1>
        </div>
        <p className="text-muted-foreground">Sign in to access your notes and data.</p>
        <SignInButton mode="modal">
          <button className="bg-teal-500 hover:bg-teal-600 text-white px-6 py-2.5 rounded-lg font-medium transition-colors">
            Sign In
          </button>
        </SignInButton>
      </div>
    </div>
  )
}

function AuthTokenSync() {
  const { getToken } = useAuth()
  useEffect(() => { setTokenGetter(getToken) }, [getToken])
  return null
}

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

const DEFAULT_DAILY_NOTE_TEMPLATE = '{YYYY}/{MM}/{YYYY}-{MM}-{DD}-daily-note'

function resolveDailyNotePath(template: string, date: Date): string {
  const year = date.getFullYear().toString()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return template
    .replace(/\{YYYY\}/g, year)
    .replace(/\{MM\}/g, month)
    .replace(/\{DD\}/g, day) + '.md'
}

function App() {
  const navigate = useNavigate()
  const location = useLocation()
  const { theme, toggleTheme, setTheme } = useTheme()

  // Fetch daily note path template from settings
  const [dailyNoteTemplate, setDailyNoteTemplate] = useState(DEFAULT_DAILY_NOTE_TEMPLATE)
  useEffect(() => {
    api.get<{ daily_note_path_template: string }>('/settings')
      .then(data => {
        if (data.daily_note_path_template) {
          setDailyNoteTemplate(data.daily_note_path_template)
        }
      })
      .catch(() => {})
  }, [])

  const view: View = useMemo(() => {
    const path = location.pathname.replace(/^\//, '')
    if (path === 'dashboard') return 'dashboard'
    if (path === 'kanban') return 'kanban'
    if (path === 'calendar') return 'calendar'
    if (path === 'profile') return 'profile'
    return 'editor'
  }, [location.pathname])

  const file = useFileManager()
  const ui = useUIState()

  const handleWizardComplete = useCallback(async (populatedContent: string, selectedTaskIds?: string[]) => {
    ui.setIsWizardOpen(false)
    file.setContent(populatedContent)
    file.contentRef.current = populatedContent
    file.setSelectedFile(ui.wizardNotePath)
    navigate(`/editor?file=${encodeURIComponent(ui.wizardNotePath)}`)
    try {
      await api.post(`/vault/file?extract=true`, { path: ui.wizardNotePath, content: populatedContent })
      file.isDirtyRef.current = false
    } catch (err) {
      console.error('Error saving wizard-populated note:', err)
    }
    // Commit rollover: update source_file for carried-forward tasks
    if (selectedTaskIds && selectedTaskIds.length > 0) {
      try {
        await api.post('/tasks/rollover', {
          task_ids: selectedTaskIds,
          new_source_file: ui.wizardNotePath,
        })
      } catch (err) {
        console.error('Error committing rollover tasks:', err)
      }
    }
  }, [ui.wizardNotePath, navigate, file, ui])

  const createDailyNote = useCallback(async () => {
    const today = new Date()
    const year = today.getFullYear()
    const month = String(today.getMonth() + 1).padStart(2, '0')
    const day = String(today.getDate()).padStart(2, '0')
    const dateStr = `${year}-${month}-${day}`
    const dailyNotePath = resolveDailyNotePath(dailyNoteTemplate, today)

    let isNewNote = false
    try {
      const data = await api.post<{ created: boolean }>(`/calendar/daily-note`, { date: dateStr })
      isNewNote = data.created
    } catch (err) {
      console.error('Error creating daily note:', err)
    }

    const fileContent = await file.fetchFileContent(dailyNotePath)
    if (isNewNote) {
      ui.setWizardDate(dateStr)
      ui.setWizardNoteContent(fileContent)
      ui.setWizardNotePath(dailyNotePath)
      ui.setIsWizardOpen(true)
    } else {
      file.setContent(fileContent)
      navigate(`/editor?file=${encodeURIComponent(dailyNotePath)}`)
      file.setSelectedFile(dailyNotePath)
    }
  }, [file, navigate, ui, dailyNoteTemplate])

  const handleFileSelect = useCallback(async (path: string) => {
    await file.handleFileSelect(path)
    if (ui.isMobile || ui.isTablet) ui.setIsMobileSidebarOpen(false)
  }, [file, ui])

  const handleSearchSelect = useCallback(async (path: string) => {
    const fileContent = await file.fetchFileContent(path)
    file.setContent(fileContent)
    file.setSelectedFile(path)
    navigate(`/editor?file=${encodeURIComponent(path)}`)
  }, [file, navigate])

  const handleCalendarDaySelect = useCallback(async (date: string, hasNote: boolean) => {
    const [yearStr, monthStr, dayStr] = date.split('-')
    const dateObj = new Date(parseInt(yearStr), parseInt(monthStr) - 1, parseInt(dayStr))
    const dailyNotePath = resolveDailyNotePath(dailyNoteTemplate, dateObj)
    if (!hasNote) {
      try { await api.post(`/calendar/daily-note`, { date }) } catch (err) { console.error('Error creating daily note:', err) }
    }
    const fileContent = await file.fetchFileContent(dailyNotePath)
    if (!hasNote) {
      ui.setWizardDate(date)
      ui.setWizardNoteContent(fileContent)
      ui.setWizardNotePath(dailyNotePath)
      ui.setIsWizardOpen(true)
    } else {
      file.setContent(fileContent)
      file.setSelectedFile(dailyNotePath)
      navigate(`/editor?file=${encodeURIComponent(dailyNotePath)}`)
    }
  }, [file, navigate, ui, dailyNoteTemplate])

  const commands = useMemo(() => createDefaultCommands({
    onSave: file.handleSave, onToggleSidebar: ui.toggleSidebar, onCreateDailyNote: createDailyNote,
    onOpenCommandPalette: ui.openCommandPalette, onSwitchToEditor: () => navigate('/editor'),
    onSwitchToDashboard: () => navigate('/dashboard'), onSwitchToKanban: () => navigate('/kanban'),
    onSwitchToCalendar: () => navigate('/calendar'), onSwitchToProfile: () => navigate('/profile'),
    onSearch: ui.openSearch, onNewFromTemplate: ui.openTemplatePicker, onQuickCapture: ui.openQuickCapture,
  }), [file.handleSave, ui, createDailyNote, navigate])

  const shortcuts: KeyboardShortcut[] = useMemo(() => [
    { key: 's', meta: true, action: file.handleSave, description: 'Save current file' },
    { key: 'k', meta: true, action: ui.openCommandPalette, description: 'Open command palette' },
    { key: 'b', meta: true, action: ui.toggleSidebar, description: 'Toggle sidebar' },
    { key: 'd', meta: true, action: createDailyNote, description: 'Create/open daily note' },
    { key: 'f', meta: true, shift: true, action: ui.openSearch, description: 'Search notes' },
    { key: 'n', meta: true, shift: true, action: ui.openQuickCapture, description: 'Quick capture' },
    { key: 't', meta: true, action: ui.openTemplatePicker, description: 'New note from template' },
  ], [file.handleSave, ui, createDailyNote])

  useKeyboardShortcuts(shortcuts)

  const sidebarContent = (
    <div className="flex flex-col h-full">
      <div className="flex border-b border-border/50">
        {(['files', 'tags', 'links'] as const).map((tab) => (
          <button
            key={tab}
            className={`flex-1 flex items-center justify-center gap-1 px-2 py-1.5 sm:py-1 text-xs font-medium transition-colors min-h-[44px] sm:min-h-0 ${
              ui.sidebarTab === tab
                ? 'bg-accent text-accent-foreground border-b-2 border-primary'
                : 'text-muted-foreground hover:text-foreground hover:bg-accent/50'
            }`}
            onClick={() => ui.setSidebarTab(tab)}
            title={tab.charAt(0).toUpperCase() + tab.slice(1)}
          >
            {tab === 'files' && <FileText className="h-4 w-4" />}
            {tab === 'tags' && <Hash className="h-4 w-4" />}
            {tab === 'links' && <Link2 className="h-4 w-4" />}
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-hidden">
        {ui.sidebarTab === 'files' && (
          <FileTree onFileSelect={handleFileSelect} selectedFile={file.selectedFile} apiBaseUrl={api.baseUrl}
            onCreateDailyNote={createDailyNote} onOpenTemplatePicker={ui.openTemplatePicker}
            onDeleteFile={file.handleDeleteFile} onRenameFile={file.handleRenameFile} />
        )}
        {ui.sidebarTab === 'tags' && <TagsPanel onFileSelect={handleFileSelect} apiBaseUrl={api.baseUrl} />}
        {ui.sidebarTab === 'links' && <BacklinksPanel currentFile={file.selectedFile} onFileSelect={handleFileSelect} apiBaseUrl={api.baseUrl} />}
      </div>
    </div>
  )

  const editorElement = (
    <>
      {!ui.isMobile && !ui.isTablet && ui.isSidebarVisible && (
        <aside className="w-64 bg-card border-r border-border/50 flex flex-col overflow-hidden">{sidebarContent}</aside>
      )}
      {(ui.isMobile || ui.isTablet) && (
        <Drawer isOpen={ui.isMobileSidebarOpen} onClose={() => ui.setIsMobileSidebarOpen(false)} position="left" title="Files">{sidebarContent}</Drawer>
      )}

      <section className="flex-1 flex flex-col min-h-0 overflow-hidden">
        {file.selectedFile ? (
          <div className="flex-1 overflow-auto p-3 sm:p-6 bg-card">
            <MarkdownEditor key={file.selectedFile} content={file.content} onChange={file.handleContentChange} onAutosave={file.handleAutosave} />
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-muted-foreground p-4 text-center">
            <p>{ui.isMobile || ui.isTablet ? 'Tap the menu to select a file' : 'Select a file to start editing'}</p>
          </div>
        )}

        {!ui.isMobile && !ui.isTablet && (
          <>
            <button onClick={() => ui.setIsChatExpanded(prev => !prev)}
              className="flex items-center justify-center gap-2 px-3 py-2 border-t border-border/50 text-xs text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors">
              <MessageSquare className="h-3.5 w-3.5" />
              <span>{ui.isChatExpanded ? 'Hide Chat' : 'Chat'}</span>
              {ui.isChatExpanded ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronUp className="h-3.5 w-3.5" />}
            </button>
            {ui.isChatExpanded && (
              <div className="h-96 border-t border-border/50 flex flex-col overflow-hidden">
                <ChatPanel apiBaseUrl={api.baseUrl} currentFile={file.selectedFile} currentContent={file.content}
                  onContentUpdate={file.handleNoteContentUpdate} initialMessage={ui.chatInitialMessage} />
              </div>
            )}
          </>
        )}
      </section>

      {(ui.isMobile || ui.isTablet) && (
        <Drawer isOpen={ui.isMobileChatOpen} onClose={() => ui.setIsMobileChatOpen(false)} position={ui.isMobile ? 'bottom' : 'right'} title="Chat">
          <ChatPanel apiBaseUrl={api.baseUrl} currentFile={file.selectedFile} currentContent={file.content}
            onContentUpdate={file.handleNoteContentUpdate} initialMessage={ui.chatInitialMessage} />
        </Drawer>
      )}
    </>
  )

  const appContent = (
    <div className={`h-screen flex flex-col overflow-hidden ${ui.isMobile ? 'pb-16' : ''}`}>
      {CLERK_ENABLED && <AuthTokenSync />}
      <header className="bg-card border-b border-border/50 px-4 sm:px-6 py-3 sm:py-4 flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-2 sm:gap-4">
          {(ui.isMobile || ui.isTablet) && view === 'editor' && (
            <Button variant="ghost" size="sm" onClick={() => ui.setIsMobileSidebarOpen(true)} className="min-w-[44px] min-h-[44px] p-0" aria-label="Open sidebar">
              <Menu className="w-5 h-5" />
            </Button>
          )}
          <div className="flex items-center gap-1.5 sm:gap-2">
            <img src="/um-logo.svg" alt="" className="w-5 h-5 sm:w-6 sm:h-6" />
            <h1 className="text-sm sm:text-base font-semibold tracking-tight truncate">{ui.isMobile ? 'UM' : 'Unstructured Minds'}</h1>
          </div>
          {!ui.isMobile && (
            <div className="hidden sm:flex items-center gap-1 bg-muted rounded-lg p-1">
              {([['editor', FileText, 'Editor'], ['dashboard', LayoutDashboard, 'Dashboard'], ['kanban', Kanban, 'Kanban'], ['profile', User, 'Profile']] as const).map(([v, Icon, label]) => (
                <Button key={v} variant={view === v ? 'secondary' : 'ghost'} size="sm" onClick={() => navigate(v === 'editor' ? '/editor' : `/${v}`)} className="gap-1">
                  <Icon className="w-4 h-4" /><span className="hidden lg:inline">{label}</span>
                </Button>
              ))}
            </div>
          )}
        </div>
        <div className="flex items-center gap-1 sm:gap-2">
          {file.saveState !== 'idle' && (
            <span className="text-xs sm:text-sm text-muted-foreground hidden sm:inline">
              {file.saveState === 'saving' && 'Saving...'}{file.saveState === 'extracting' && 'Saving & extracting...'}{file.saveState === 'saved' && 'Saved'}
            </span>
          )}
          {(ui.isMobile || ui.isTablet) && view === 'editor' && (
            <Button variant="ghost" size="sm" onClick={() => ui.setIsMobileChatOpen(true)} className="min-w-[44px] min-h-[44px] p-0" aria-label="Open chat">
              <MessageSquare className="w-5 h-5" />
            </Button>
          )}
          <Button variant="ghost" size="sm" onClick={ui.openSearch} aria-label="Search notes" title="Search notes (Cmd+Shift+F)" className="min-w-[44px] min-h-[44px] sm:min-w-0 sm:min-h-0 p-0 sm:p-2">
            <Search className="w-4 h-4" />
          </Button>
          <Button variant="ghost" size="sm" onClick={toggleTheme} aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`} className="min-w-[44px] min-h-[44px] sm:min-w-0 sm:min-h-0 p-0 sm:p-2">
            {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </Button>
          <Button variant="outline" size="sm" onClick={() => ui.setIsSettingsOpen(true)} className="gap-1 min-h-[44px] sm:min-h-0 sm:h-8">
            <Settings className="w-4 h-4" /><span className="hidden sm:inline">Settings</span>
          </Button>
          {CLERK_ENABLED && <UserButton afterSignOutUrl="/" />}
        </div>
      </header>

      <main className="flex-1 flex overflow-hidden">
        <Routes>
          <Route path="/dashboard" element={<Suspense fallback={<ViewLoadingFallback />}><section className="flex-1 overflow-auto bg-background"><Dashboard apiUrl={api.baseUrl} onCreateNote={createDailyNote} /></section></Suspense>} />
          <Route path="/kanban" element={<Suspense fallback={<ViewLoadingFallback />}><section className="flex-1 overflow-auto bg-background"><KanbanBoard apiUrl={api.baseUrl} onFileSelect={handleFileSelect} /></section></Suspense>} />
          <Route path="/calendar" element={<Suspense fallback={<ViewLoadingFallback />}><section className="flex-1 overflow-auto bg-background"><CalendarView apiUrl={api.baseUrl} onDaySelect={handleCalendarDaySelect} /></section></Suspense>} />
          <Route path="/profile" element={<Suspense fallback={<ViewLoadingFallback />}><section className="flex-1 overflow-auto bg-background"><LifeProfile apiUrl={api.baseUrl} /></section></Suspense>} />
          <Route path="/editor" element={editorElement} />
          <Route path="/" element={editorElement} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>

      {ui.isMobile && <MobileNav currentView={view} onViewChange={(v) => navigate(v === 'editor' ? '/editor' : `/${v}`)} />}
      <CommandPalette isOpen={ui.isCommandPaletteOpen} onClose={() => ui.setIsCommandPaletteOpen(false)} commands={commands} />
      <SettingsPanel isOpen={ui.isSettingsOpen} onClose={() => ui.setIsSettingsOpen(false)} apiBaseUrl={api.baseUrl} onThemeChange={setTheme} />
      <SearchModal isOpen={ui.isSearchOpen} onClose={() => ui.setIsSearchOpen(false)} onSelect={handleSearchSelect} apiBaseUrl={api.baseUrl} />
      <TemplatePicker isOpen={ui.isTemplatePickerOpen} onClose={() => ui.setIsTemplatePickerOpen(false)} onSelect={handleSearchSelect} apiBaseUrl={api.baseUrl} />
      <QuickCapture isOpen={ui.isQuickCaptureOpen} onClose={() => ui.setIsQuickCaptureOpen(false)} apiBaseUrl={api.baseUrl} />
      <DailyNoteWizard isOpen={ui.isWizardOpen} onClose={() => ui.setIsWizardOpen(false)} onComplete={handleWizardComplete} noteContent={ui.wizardNoteContent} date={ui.wizardDate} apiBaseUrl={api.baseUrl} />
    </div>
  )

  if (!CLERK_ENABLED) return appContent

  return (
    <>
      <SignedIn>{appContent}</SignedIn>
      <SignedOut><SignInGate /></SignedOut>
    </>
  )
}

export default App
