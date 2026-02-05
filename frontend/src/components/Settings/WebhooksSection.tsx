import { useState, useEffect, useCallback } from 'react'
import {
  Webhook,
  Plus,
  Trash2,
  Play,
  CheckCircle,
  XCircle,
  Loader2,
  ToggleLeft,
  ToggleRight,
  AlertCircle,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface WebhookData {
  id: string
  url: string
  events: string[]
  name: string | null
  active: boolean
  created_at: string
  updated_at: string
  last_triggered: string | null
  failure_count: number
}

interface WebhooksSectionProps {
  apiBaseUrl: string
}

const AVAILABLE_EVENTS = [
  { value: 'note.created', label: 'Note Created' },
  { value: 'note.updated', label: 'Note Updated' },
  { value: 'note.deleted', label: 'Note Deleted' },
  { value: 'extraction.completed', label: 'Extraction Completed' },
  { value: 'daily.created', label: 'Daily Note Created' },
]

export function WebhooksSection({ apiBaseUrl }: WebhooksSectionProps) {
  const [webhooks, setWebhooks] = useState<WebhookData[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isAddingNew, setIsAddingNew] = useState(false)
  const [testResults, setTestResults] = useState<Record<string, { success: boolean; message: string } | null>>({})
  const [testingIds, setTestingIds] = useState<Set<string>>(new Set())

  // Form state for new webhook
  const [newUrl, setNewUrl] = useState('')
  const [newName, setNewName] = useState('')
  const [newSecret, setNewSecret] = useState('')
  const [selectedEvents, setSelectedEvents] = useState<string[]>(['note.created', 'note.updated'])
  const [isSaving, setIsSaving] = useState(false)

  const fetchWebhooks = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await fetch(`${apiBaseUrl}/webhooks`)
      if (!response.ok) {
        throw new Error('Failed to fetch webhooks')
      }
      const data = await response.json()
      setWebhooks(data.webhooks || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setIsLoading(false)
    }
  }, [apiBaseUrl])

  useEffect(() => {
    fetchWebhooks()
  }, [fetchWebhooks])

  const handleCreateWebhook = async () => {
    if (!newUrl || selectedEvents.length === 0) {
      setError('URL and at least one event are required')
      return
    }

    setIsSaving(true)
    setError(null)
    try {
      const response = await fetch(`${apiBaseUrl}/webhooks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: newUrl,
          events: selectedEvents,
          name: newName || null,
          secret: newSecret || null,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to create webhook')
      }

      // Reset form and refresh list
      setNewUrl('')
      setNewName('')
      setNewSecret('')
      setSelectedEvents(['note.created', 'note.updated'])
      setIsAddingNew(false)
      await fetchWebhooks()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setIsSaving(false)
    }
  }

  const handleDeleteWebhook = async (id: string) => {
    if (!confirm('Are you sure you want to delete this webhook?')) {
      return
    }

    try {
      const response = await fetch(`${apiBaseUrl}/webhooks/${id}`, {
        method: 'DELETE',
      })

      if (!response.ok) {
        throw new Error('Failed to delete webhook')
      }

      await fetchWebhooks()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    }
  }

  const handleToggleWebhook = async (id: string) => {
    try {
      const response = await fetch(`${apiBaseUrl}/webhooks/${id}/toggle`, {
        method: 'POST',
      })

      if (!response.ok) {
        throw new Error('Failed to toggle webhook')
      }

      await fetchWebhooks()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    }
  }

  const handleTestWebhook = async (id: string) => {
    setTestingIds(prev => new Set(prev).add(id))
    setTestResults(prev => ({ ...prev, [id]: null }))

    try {
      const response = await fetch(`${apiBaseUrl}/webhooks/${id}/test`, {
        method: 'POST',
      })

      const result = await response.json()
      setTestResults(prev => ({
        ...prev,
        [id]: {
          success: result.success,
          message: result.success
            ? `Success (${result.status_code}) - ${Math.round(result.duration_ms)}ms`
            : result.error || `Failed (${result.status_code})`,
        },
      }))
    } catch (err) {
      setTestResults(prev => ({
        ...prev,
        [id]: {
          success: false,
          message: err instanceof Error ? err.message : 'Test failed',
        },
      }))
    } finally {
      setTestingIds(prev => {
        const next = new Set(prev)
        next.delete(id)
        return next
      })
    }
  }

  const toggleEventSelection = (event: string) => {
    setSelectedEvents(prev =>
      prev.includes(event)
        ? prev.filter(e => e !== event)
        : [...prev, event]
    )
  }

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'Never'
    const date = new Date(dateStr)
    return date.toLocaleString()
  }

  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Webhook className="w-4 h-4 text-cyan-400" />
          <h3 className="text-sm font-semibold text-zinc-300 uppercase tracking-wide">
            Webhooks
          </h3>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setIsAddingNew(!isAddingNew)}
          className="h-7 px-2 text-xs"
        >
          <Plus className="w-3 h-3 mr-1" />
          Add
        </Button>
      </div>

      {error && (
        <div className="text-red-400 bg-red-400/10 rounded-lg p-3 text-sm mb-3 flex items-center gap-2">
          <AlertCircle className="w-4 h-4" />
          {error}
        </div>
      )}

      {/* Add New Webhook Form */}
      {isAddingNew && (
        <div className="bg-zinc-800/50 rounded-lg p-4 mb-3 space-y-3">
          <div>
            <label className="text-xs text-zinc-400 block mb-1">Webhook URL *</label>
            <input
              type="url"
              value={newUrl}
              onChange={e => setNewUrl(e.target.value)}
              placeholder="https://example.com/webhook"
              className="w-full bg-zinc-900 border border-zinc-700 rounded-md px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="text-xs text-zinc-400 block mb-1">Name (optional)</label>
            <input
              type="text"
              value={newName}
              onChange={e => setNewName(e.target.value)}
              placeholder="My Integration"
              className="w-full bg-zinc-900 border border-zinc-700 rounded-md px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="text-xs text-zinc-400 block mb-1">Secret (optional, min 16 chars)</label>
            <input
              type="password"
              value={newSecret}
              onChange={e => setNewSecret(e.target.value)}
              placeholder="your-secret-key-here"
              className="w-full bg-zinc-900 border border-zinc-700 rounded-md px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="text-xs text-zinc-400 block mb-2">Events *</label>
            <div className="flex flex-wrap gap-2">
              {AVAILABLE_EVENTS.map(event => (
                <button
                  key={event.value}
                  onClick={() => toggleEventSelection(event.value)}
                  className={cn(
                    'px-2 py-1 rounded text-xs font-medium transition-colors',
                    selectedEvents.includes(event.value)
                      ? 'bg-blue-500 text-white'
                      : 'bg-zinc-700 text-zinc-300 hover:bg-zinc-600'
                  )}
                >
                  {event.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex gap-2 pt-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsAddingNew(false)}
              disabled={isSaving}
            >
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={handleCreateWebhook}
              disabled={isSaving || !newUrl || selectedEvents.length === 0}
            >
              {isSaving ? (
                <>
                  <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                  Saving...
                </>
              ) : (
                'Create Webhook'
              )}
            </Button>
          </div>
        </div>
      )}

      {/* Webhooks List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-4">
          <Loader2 className="w-5 h-5 animate-spin text-zinc-400" />
        </div>
      ) : webhooks.length === 0 ? (
        <div className="bg-zinc-800/50 rounded-lg p-4 text-center">
          <Webhook className="w-8 h-8 mx-auto mb-2 text-zinc-600" />
          <p className="text-sm text-zinc-400">No webhooks configured</p>
          <p className="text-xs text-zinc-500 mt-1">
            Add a webhook to receive notifications for events
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {webhooks.map(webhook => (
            <div
              key={webhook.id}
              className={cn(
                'bg-zinc-800/50 rounded-lg p-3',
                !webhook.active && 'opacity-60'
              )}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-zinc-200 truncate">
                      {webhook.name || 'Unnamed Webhook'}
                    </span>
                    {webhook.failure_count > 0 && (
                      <span className="text-xs bg-red-500/20 text-red-400 px-1.5 py-0.5 rounded">
                        {webhook.failure_count} failures
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-zinc-500 truncate mt-0.5" title={webhook.url}>
                    {webhook.url}
                  </p>
                  <div className="flex flex-wrap gap-1 mt-2">
                    {webhook.events.map(event => (
                      <span
                        key={event}
                        className="text-xs bg-zinc-700 text-zinc-300 px-1.5 py-0.5 rounded"
                      >
                        {event}
                      </span>
                    ))}
                  </div>
                  <p className="text-xs text-zinc-500 mt-2">
                    Last triggered: {formatDate(webhook.last_triggered)}
                  </p>
                </div>

                <div className="flex items-center gap-1">
                  {/* Test Button */}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleTestWebhook(webhook.id)}
                    disabled={testingIds.has(webhook.id)}
                    className="h-7 w-7 p-0"
                    title="Test webhook"
                  >
                    {testingIds.has(webhook.id) ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Play className="w-3.5 h-3.5" />
                    )}
                  </Button>

                  {/* Toggle Button */}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleToggleWebhook(webhook.id)}
                    className="h-7 w-7 p-0"
                    title={webhook.active ? 'Disable webhook' : 'Enable webhook'}
                  >
                    {webhook.active ? (
                      <ToggleRight className="w-4 h-4 text-green-400" />
                    ) : (
                      <ToggleLeft className="w-4 h-4 text-zinc-400" />
                    )}
                  </Button>

                  {/* Delete Button */}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDeleteWebhook(webhook.id)}
                    className="h-7 w-7 p-0 text-red-400 hover:text-red-300 hover:bg-red-400/10"
                    title="Delete webhook"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </Button>
                </div>
              </div>

              {/* Test Result */}
              {testResults[webhook.id] && (
                <div
                  className={cn(
                    'mt-2 p-2 rounded text-xs flex items-center gap-1.5',
                    testResults[webhook.id]?.success
                      ? 'bg-green-500/10 text-green-400'
                      : 'bg-red-500/10 text-red-400'
                  )}
                >
                  {testResults[webhook.id]?.success ? (
                    <CheckCircle className="w-3.5 h-3.5" />
                  ) : (
                    <XCircle className="w-3.5 h-3.5" />
                  )}
                  {testResults[webhook.id]?.message}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
