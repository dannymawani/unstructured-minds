import { useState, useEffect, useCallback, useRef } from 'react'
import { X, Folder, Palette, Check, Loader2, Download, Upload, Database, Archive } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface Settings {
  theme: string
}

type Theme = 'light' | 'dark'

interface SettingsPanelProps {
  isOpen: boolean
  onClose: () => void
  apiBaseUrl?: string
  onThemeChange?: (theme: Theme) => void
}

export function SettingsPanel({
  isOpen,
  onClose,
  apiBaseUrl = '',
  onThemeChange,
}: SettingsPanelProps) {
  const [settings, setSettings] = useState<Settings | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [exportStatus, setExportStatus] = useState<string | null>(null)
  const [isExporting, setIsExporting] = useState(false)
  const [isImporting, setIsImporting] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const fetchSettings = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await fetch(`${apiBaseUrl}/settings`)
      if (!response.ok) {
        throw new Error('Failed to fetch settings')
      }
      const data = await response.json()
      setSettings(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setIsLoading(false)
    }
  }, [apiBaseUrl])

  useEffect(() => {
    if (isOpen) {
      fetchSettings()
    }
  }, [isOpen, fetchSettings])

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown)
      return () => document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen, onClose])

  const handleThemeChange = async (theme: Theme) => {
    if (!settings) return
    setIsSaving(true)
    try {
      const response = await fetch(`${apiBaseUrl}/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ theme }),
      })
      if (!response.ok) {
        throw new Error('Failed to update settings')
      }
      const data = await response.json()
      setSettings(data)
      onThemeChange?.(theme)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setIsSaving(false)
    }
  }

  const handleExportVault = async () => {
    setIsExporting(true)
    setExportStatus(null)
    try {
      const response = await fetch(`${apiBaseUrl}/export/vault`)
      if (!response.ok) {
        throw new Error('Failed to export vault')
      }
      const blob = await response.blob()
      const contentDisposition = response.headers.get('Content-Disposition')
      const filename = contentDisposition
        ? contentDisposition.split('filename=')[1]?.replace(/"/g, '')
        : 'vault_export.zip'

      // Trigger download
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)

      setExportStatus('Vault exported successfully')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Export failed')
    } finally {
      setIsExporting(false)
    }
  }

  const handleExportData = async () => {
    setIsExporting(true)
    setExportStatus(null)
    try {
      const response = await fetch(`${apiBaseUrl}/export/data?format=csv`)
      if (!response.ok) {
        throw new Error('Failed to export data')
      }
      const blob = await response.blob()
      const contentDisposition = response.headers.get('Content-Disposition')
      const filename = contentDisposition
        ? contentDisposition.split('filename=')[1]?.replace(/"/g, '')
        : `data_export.zip`

      // Trigger download
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)

      setExportStatus('Data exported as ZIP')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Export failed')
    } finally {
      setIsExporting(false)
    }
  }

  const handleImportVault = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    setIsImporting(true)
    setExportStatus(null)
    setError(null)

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch(`${apiBaseUrl}/import/vault`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to import vault')
      }

      const result = await response.json()
      setExportStatus(`Imported ${result.files_imported} files successfully`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Import failed')
    } finally {
      setIsImporting(false)
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div
        className="bg-popover border border-border rounded-lg w-full max-w-lg max-h-[85vh] overflow-hidden flex flex-col text-foreground"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <h2 className="text-lg font-semibold text-foreground">Settings</h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-muted rounded transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
            </div>
          ) : error ? (
            <div className="text-red-400 bg-red-400/10 rounded-lg p-4 text-sm">
              {error}
            </div>
          ) : settings ? (
            <>
              {/* Appearance Section */}
              <section>
                <div className="flex items-center gap-2 mb-3">
                  <Palette className="w-4 h-4 text-purple-400" />
                  <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                    Appearance
                  </h3>
                </div>
                <div className="space-y-3">
                  <div className="flex items-center justify-between bg-muted rounded-lg p-3">
                    <span className="text-sm text-muted-foreground">Theme</span>
                    <div className="flex gap-2">
                      <ThemeButton
                        theme="dark"
                        currentTheme={settings.theme}
                        onClick={() => handleThemeChange('dark')}
                        disabled={isSaving}
                      />
                      <ThemeButton
                        theme="light"
                        currentTheme={settings.theme}
                        onClick={() => handleThemeChange('light')}
                        disabled={isSaving}
                      />
                    </div>
                  </div>
                </div>
              </section>

              {/* Export/Import Section */}
              <section>
                <div className="flex items-center gap-2 mb-3">
                  <Archive className="w-4 h-4 text-orange-400" />
                  <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                    Backup & Export
                  </h3>
                </div>
                <div className="space-y-3">
                  {/* Export Vault */}
                  <div className="bg-muted rounded-lg p-3">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Folder className="w-4 h-4 text-muted-foreground" />
                        <span className="text-sm text-muted-foreground">Export Notes</span>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleExportVault}
                        disabled={isExporting}
                        className="h-7 px-2 text-xs"
                      >
                        {isExporting ? (
                          <Loader2 className="w-3 h-3 animate-spin" />
                        ) : (
                          <Download className="w-3 h-3" />
                        )}
                        <span className="ml-1">ZIP</span>
                      </Button>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Your raw markdown notes
                    </p>
                  </div>

                  {/* Export Data */}
                  <div className="bg-muted rounded-lg p-3">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Database className="w-4 h-4 text-muted-foreground" />
                        <span className="text-sm text-muted-foreground">Export Data</span>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleExportData}
                        disabled={isExporting}
                        className="h-7 px-2 text-xs"
                      >
                        {isExporting ? (
                          <Loader2 className="w-3 h-3 animate-spin" />
                        ) : (
                          <Download className="w-3 h-3" />
                        )}
                        <span className="ml-1">ZIP</span>
                      </Button>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Extracted tables (exercises, food, metrics, tasks) as CSV
                    </p>
                  </div>

                  {/* Import Vault */}
                  <div className="bg-muted rounded-lg p-3">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Upload className="w-4 h-4 text-muted-foreground" />
                        <span className="text-sm text-muted-foreground">Import Vault</span>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => fileInputRef.current?.click()}
                        disabled={isImporting}
                        className="h-7 px-2 text-xs"
                      >
                        {isImporting ? (
                          <Loader2 className="w-3 h-3 animate-spin" />
                        ) : (
                          <Upload className="w-3 h-3" />
                        )}
                        <span className="ml-1">Upload</span>
                      </Button>
                      <input
                        ref={fileInputRef}
                        type="file"
                        accept=".zip"
                        onChange={handleImportVault}
                        className="hidden"
                      />
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Restore vault from a ZIP backup
                    </p>
                  </div>

                  {/* Status message */}
                  {exportStatus && (
                    <div className="text-green-400 bg-green-400/10 rounded-lg p-3 text-sm flex items-center gap-2">
                      <Check className="w-4 h-4" />
                      {exportStatus}
                    </div>
                  )}
                </div>
              </section>

            </>
          ) : null}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-border">
          <Button variant="outline" onClick={onClose} className="w-full">
            Close
          </Button>
        </div>
      </div>
    </div>
  )
}

interface ThemeButtonProps {
  theme: string
  currentTheme: string
  onClick: () => void
  disabled?: boolean
}

function ThemeButton({ theme, currentTheme, onClick, disabled }: ThemeButtonProps) {
  const isActive = theme === currentTheme
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'px-3 py-1.5 rounded-md text-sm font-medium transition-colors',
        'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 focus:ring-offset-popover',
        isActive
          ? 'bg-primary text-primary-foreground'
          : 'bg-secondary text-muted-foreground hover:bg-secondary/80',
        disabled && 'opacity-50 cursor-not-allowed'
      )}
    >
      <span className="flex items-center gap-1.5">
        {isActive && <Check className="w-3 h-3" />}
        {theme.charAt(0).toUpperCase() + theme.slice(1)}
      </span>
    </button>
  )
}


