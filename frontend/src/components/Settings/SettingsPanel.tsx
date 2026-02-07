import { useState, useEffect, useCallback, useRef } from 'react'
import { X, Folder, Palette, Key, Check, Loader2, Download, Upload, Database, Archive, FileJson } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { SchemaManager } from '@/components/Schemas'

interface Settings {
  vault_path: string
  data_path: string
  claude_enabled: boolean
  claude_configured: boolean
  api_key_set: boolean
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

  const handleExportData = async (format: 'csv' | 'json') => {
    setIsExporting(true)
    setExportStatus(null)
    try {
      const response = await fetch(`${apiBaseUrl}/export/data?format=${format}`)
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

      setExportStatus(`Data exported as ${format.toUpperCase()}`)
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
        className="bg-zinc-900 border border-zinc-700 rounded-xl w-full max-w-lg max-h-[85vh] overflow-hidden flex flex-col text-zinc-100"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-zinc-700">
          <h2 className="text-lg font-semibold text-zinc-100">Settings</h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-zinc-800 rounded transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-zinc-400" />
            </div>
          ) : error ? (
            <div className="text-red-400 bg-red-400/10 rounded-lg p-4 text-sm">
              {error}
            </div>
          ) : settings ? (
            <>
              {/* General Section */}
              <section>
                <div className="flex items-center gap-2 mb-3">
                  <Folder className="w-4 h-4 text-blue-400" />
                  <h3 className="text-sm font-semibold text-zinc-300 uppercase tracking-wide">
                    General
                  </h3>
                </div>
                <div className="space-y-3">
                  <SettingItem label="Vault Path" value={settings.vault_path} />
                  <SettingItem label="Data Path" value={settings.data_path} />
                </div>
              </section>

              {/* Appearance Section */}
              <section>
                <div className="flex items-center gap-2 mb-3">
                  <Palette className="w-4 h-4 text-purple-400" />
                  <h3 className="text-sm font-semibold text-zinc-300 uppercase tracking-wide">
                    Appearance
                  </h3>
                </div>
                <div className="space-y-3">
                  <div className="flex items-center justify-between bg-zinc-800/50 rounded-lg p-3">
                    <span className="text-sm text-zinc-300">Theme</span>
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

              {/* API Section */}
              <section>
                <div className="flex items-center gap-2 mb-3">
                  <Key className="w-4 h-4 text-green-400" />
                  <h3 className="text-sm font-semibold text-zinc-300 uppercase tracking-wide">
                    API
                  </h3>
                </div>
                <div className="space-y-3">
                  <div className="flex items-center justify-between bg-zinc-800/50 rounded-lg p-3">
                    <span className="text-sm text-zinc-300">Claude API</span>
                    <ApiStatus
                      enabled={settings.claude_enabled}
                      configured={settings.claude_configured}
                      keySet={settings.api_key_set}
                    />
                  </div>
                </div>
              </section>

              {/* Schemas Section */}
              <section>
                <div className="flex items-center gap-2 mb-3">
                  <FileJson className="w-4 h-4 text-cyan-400" />
                  <h3 className="text-sm font-semibold text-zinc-300 uppercase tracking-wide">
                    Data Extraction
                  </h3>
                </div>
                <div className="bg-zinc-800/50 rounded-lg p-3">
                  <SchemaManager apiBaseUrl={apiBaseUrl} />
                </div>
              </section>

              {/* Export/Import Section */}
              <section>
                <div className="flex items-center gap-2 mb-3">
                  <Archive className="w-4 h-4 text-orange-400" />
                  <h3 className="text-sm font-semibold text-zinc-300 uppercase tracking-wide">
                    Backup & Export
                  </h3>
                </div>
                <div className="space-y-3">
                  {/* Export Vault */}
                  <div className="bg-zinc-800/50 rounded-lg p-3">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Folder className="w-4 h-4 text-zinc-400" />
                        <span className="text-sm text-zinc-300">Export Vault</span>
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
                    <p className="text-xs text-zinc-500">
                      Download all vault files as a ZIP archive
                    </p>
                  </div>

                  {/* Export Data */}
                  <div className="bg-zinc-800/50 rounded-lg p-3">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Database className="w-4 h-4 text-zinc-400" />
                        <span className="text-sm text-zinc-300">Export Data</span>
                      </div>
                      <div className="flex gap-1">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleExportData('csv')}
                          disabled={isExporting}
                          className="h-7 px-2 text-xs"
                        >
                          {isExporting ? (
                            <Loader2 className="w-3 h-3 animate-spin" />
                          ) : (
                            <Download className="w-3 h-3" />
                          )}
                          <span className="ml-1">CSV</span>
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleExportData('json')}
                          disabled={isExporting}
                          className="h-7 px-2 text-xs"
                        >
                          {isExporting ? (
                            <Loader2 className="w-3 h-3 animate-spin" />
                          ) : (
                            <Download className="w-3 h-3" />
                          )}
                          <span className="ml-1">JSON</span>
                        </Button>
                      </div>
                    </div>
                    <p className="text-xs text-zinc-500">
                      Download extracted data tables
                    </p>
                  </div>

                  {/* Import Vault */}
                  <div className="bg-zinc-800/50 rounded-lg p-3">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Upload className="w-4 h-4 text-zinc-400" />
                        <span className="text-sm text-zinc-300">Import Vault</span>
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
                    <p className="text-xs text-zinc-500">
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
        <div className="p-4 border-t border-zinc-700">
          <Button variant="outline" onClick={onClose} className="w-full">
            Close
          </Button>
        </div>
      </div>
    </div>
  )
}

interface SettingItemProps {
  label: string
  value: string
}

function SettingItem({ label, value }: SettingItemProps) {
  return (
    <div className="bg-zinc-800/50 rounded-lg p-3">
      <span className="text-xs text-zinc-500 block mb-1">{label}</span>
      <span className="text-sm text-zinc-300 font-mono break-all">{value}</span>
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
        'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-zinc-900',
        isActive
          ? 'bg-blue-500 text-white'
          : 'bg-zinc-700 text-zinc-300 hover:bg-zinc-600',
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

interface ApiStatusProps {
  enabled: boolean
  configured: boolean
  keySet: boolean
}

function ApiStatus({ enabled, configured, keySet }: ApiStatusProps) {
  if (!enabled) {
    return (
      <span className="text-xs bg-zinc-700 text-zinc-400 px-2 py-1 rounded">
        Disabled
      </span>
    )
  }

  if (!keySet) {
    return (
      <span className="text-xs bg-red-500/20 text-red-400 px-2 py-1 rounded">
        API Key Not Set
      </span>
    )
  }

  if (!configured) {
    return (
      <span className="text-xs bg-yellow-500/20 text-yellow-400 px-2 py-1 rounded">
        Not Configured
      </span>
    )
  }

  return (
    <span className="text-xs bg-green-500/20 text-green-400 px-2 py-1 rounded flex items-center gap-1">
      <Check className="w-3 h-3" />
      Configured
    </span>
  )
}

