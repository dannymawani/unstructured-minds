import { useState, useCallback } from 'react'
import { useMobile } from '@/hooks/useMobile'

export function useUIState() {
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false)
  const [isSidebarVisible, setIsSidebarVisible] = useState(true)
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  const [isSearchOpen, setIsSearchOpen] = useState(false)
  const [isTemplatePickerOpen, setIsTemplatePickerOpen] = useState(false)
  const [isQuickCaptureOpen, setIsQuickCaptureOpen] = useState(false)

  // Mobile state
  const { isMobile, isTablet } = useMobile()
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false)
  const [isMobileChatOpen, setIsMobileChatOpen] = useState(false)
  const [isChatExpanded, setIsChatExpanded] = useState(false)
  const [chatInitialMessage, setChatInitialMessage] = useState<string | undefined>()

  // Wizard state
  const [isWizardOpen, setIsWizardOpen] = useState(false)
  const [wizardDate, setWizardDate] = useState('')
  const [wizardNoteContent, setWizardNoteContent] = useState('')
  const [wizardNotePath, setWizardNotePath] = useState('')

  const toggleSidebar = useCallback(() => {
    if (isMobile || isTablet) {
      setIsMobileSidebarOpen((prev) => !prev)
    } else {
      setIsSidebarVisible((prev) => !prev)
    }
  }, [isMobile, isTablet])

  const openCommandPalette = useCallback(() => setIsCommandPaletteOpen(true), [])
  const openSearch = useCallback(() => setIsSearchOpen(true), [])
  const openTemplatePicker = useCallback(() => setIsTemplatePickerOpen(true), [])
  const openQuickCapture = useCallback(() => setIsQuickCaptureOpen(true), [])

  return {
    // Sidebar
    isSidebarVisible,
    toggleSidebar,

    // Modals
    isCommandPaletteOpen,
    setIsCommandPaletteOpen,
    isSettingsOpen,
    setIsSettingsOpen,
    isSearchOpen,
    setIsSearchOpen,
    isTemplatePickerOpen,
    setIsTemplatePickerOpen,
    isQuickCaptureOpen,
    setIsQuickCaptureOpen,
    openCommandPalette,
    openSearch,
    openTemplatePicker,
    openQuickCapture,

    // Mobile
    isMobile,
    isTablet,
    isMobileSidebarOpen,
    setIsMobileSidebarOpen,
    isMobileChatOpen,
    setIsMobileChatOpen,
    isChatExpanded,
    setIsChatExpanded,
    chatInitialMessage,
    setChatInitialMessage,

    // Wizard
    isWizardOpen,
    setIsWizardOpen,
    wizardDate,
    setWizardDate,
    wizardNoteContent,
    setWizardNoteContent,
    wizardNotePath,
    setWizardNotePath,
  }
}
