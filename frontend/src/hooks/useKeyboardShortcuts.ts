import { useEffect, useCallback } from 'react'

export interface KeyboardShortcut {
  key: string
  ctrl?: boolean
  meta?: boolean
  shift?: boolean
  alt?: boolean
  action: () => void
  description: string
}

interface UseKeyboardShortcutsOptions {
  enabled?: boolean
}

/**
 * Centralized keyboard shortcut handler.
 * Registers global keyboard shortcuts and handles cleanup.
 */
export function useKeyboardShortcuts(
  shortcuts: KeyboardShortcut[],
  options: UseKeyboardShortcutsOptions = {}
) {
  const { enabled = true } = options

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!enabled) return

      // Skip if user is typing in an input/textarea (except for specific shortcuts)
      const target = e.target as HTMLElement
      const isEditing =
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable

      for (const shortcut of shortcuts) {
        const metaOrCtrl = shortcut.meta || shortcut.ctrl
        const keyMatches = e.key.toLowerCase() === shortcut.key.toLowerCase()
        const metaMatches = metaOrCtrl ? e.metaKey || e.ctrlKey : true
        const shiftMatches = shortcut.shift ? e.shiftKey : !e.shiftKey
        const altMatches = shortcut.alt ? e.altKey : !e.altKey

        if (keyMatches && metaMatches && shiftMatches && altMatches) {
          // Allow specific shortcuts even in editing mode
          const allowedInEditing = ['s', 'f', 'k', 'b']
          if (isEditing && !allowedInEditing.includes(shortcut.key.toLowerCase())) {
            continue
          }
          e.preventDefault()
          shortcut.action()
          return
        }
      }
    },
    [shortcuts, enabled]
  )

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])
}

/**
 * Returns the display string for a keyboard shortcut (e.g., "Cmd+K")
 */
export function getShortcutDisplay(shortcut: KeyboardShortcut): string {
  const parts: string[] = []
  const isMac = typeof navigator !== 'undefined' && navigator.platform.includes('Mac')

  if (shortcut.ctrl || shortcut.meta) {
    parts.push(isMac ? 'Cmd' : 'Ctrl')
  }
  if (shortcut.shift) {
    parts.push('Shift')
  }
  if (shortcut.alt) {
    parts.push(isMac ? 'Option' : 'Alt')
  }
  parts.push(shortcut.key.toUpperCase())

  return parts.join('+')
}
