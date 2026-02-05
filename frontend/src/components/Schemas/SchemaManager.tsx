import { useState, useEffect, useCallback } from 'react'
import {
  Plus,
  Trash2,
  Edit2,
  ChevronDown,
  ChevronRight,
  Loader2,
  Check,
  X,
  AlertCircle,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

// Types
interface SchemaField {
  name: string
  type: 'string' | 'integer' | 'number' | 'boolean' | 'array'
  required: boolean
  description?: string
  min?: number
  max?: number
  enum?: string[]
}

interface SchemaListItem {
  name: string
  description: string
  is_builtin: boolean
  field_count: number
}

interface SchemaDefinition {
  name: string
  description: string
  fields: SchemaField[]
  extraction_hints?: string
}

interface SchemaManagerProps {
  apiBaseUrl?: string
}

const FIELD_TYPES = ['string', 'integer', 'number', 'boolean', 'array'] as const

export function SchemaManager({ apiBaseUrl = '' }: SchemaManagerProps) {
  const [schemas, setSchemas] = useState<SchemaListItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedSchema, setExpandedSchema] = useState<string | null>(null)
  const [schemaDetails, setSchemaDetails] = useState<Record<string, SchemaDefinition>>({})
  const [isEditing, setIsEditing] = useState<string | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const [editForm, setEditForm] = useState<SchemaDefinition | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)

  // Fetch schemas list
  const fetchSchemas = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await fetch(`${apiBaseUrl}/schemas`)
      if (!response.ok) throw new Error('Failed to fetch schemas')
      const data = await response.json()
      setSchemas(data.schemas)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setIsLoading(false)
    }
  }, [apiBaseUrl])

  useEffect(() => {
    fetchSchemas()
  }, [fetchSchemas])

  // Fetch schema details
  const fetchSchemaDetails = useCallback(
    async (name: string) => {
      if (schemaDetails[name]) return
      try {
        const response = await fetch(`${apiBaseUrl}/schemas/${name}`)
        if (!response.ok) throw new Error('Failed to fetch schema details')
        const data = await response.json()
        setSchemaDetails((prev) => ({ ...prev, [name]: data }))
      } catch (err) {
        console.error('Error fetching schema details:', err)
      }
    },
    [apiBaseUrl, schemaDetails]
  )

  // Toggle schema expansion
  const toggleSchema = (name: string) => {
    if (expandedSchema === name) {
      setExpandedSchema(null)
    } else {
      setExpandedSchema(name)
      fetchSchemaDetails(name)
    }
  }

  // Start creating a new schema
  const startCreate = () => {
    setIsCreating(true)
    setEditForm({
      name: '',
      description: '',
      fields: [{ name: '', type: 'string', required: false }],
      extraction_hints: '',
    })
  }

  // Start editing a schema
  const startEdit = (schema: SchemaDefinition) => {
    setIsEditing(schema.name)
    setEditForm({ ...schema })
  }

  // Cancel editing
  const cancelEdit = () => {
    setIsCreating(false)
    setIsEditing(null)
    setEditForm(null)
  }

  // Save schema
  const saveSchema = async () => {
    if (!editForm) return

    // Validate
    if (!editForm.name.match(/^[a-z][a-z0-9_]*$/)) {
      setError('Schema name must start with lowercase letter and contain only lowercase letters, numbers, and underscores')
      return
    }
    if (!editForm.description) {
      setError('Description is required')
      return
    }
    if (editForm.fields.length === 0) {
      setError('At least one field is required')
      return
    }
    for (const field of editForm.fields) {
      if (!field.name.match(/^[a-zA-Z][a-zA-Z0-9_]*$/)) {
        setError(`Invalid field name: ${field.name || '(empty)'}`)
        return
      }
    }

    setIsSaving(true)
    setError(null)

    try {
      const url = isCreating
        ? `${apiBaseUrl}/schemas`
        : `${apiBaseUrl}/schemas/${isEditing}`
      const method = isCreating ? 'POST' : 'PUT'

      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editForm),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to save schema')
      }

      // Refresh schemas list
      await fetchSchemas()
      cancelEdit()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setIsSaving(false)
    }
  }

  // Delete schema
  const deleteSchema = async (name: string) => {
    try {
      const response = await fetch(`${apiBaseUrl}/schemas/${name}`, {
        method: 'DELETE',
      })
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to delete schema')
      }
      await fetchSchemas()
      setDeleteConfirm(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    }
  }

  // Update form field
  const updateField = (index: number, updates: Partial<SchemaField>) => {
    if (!editForm) return
    const newFields = [...editForm.fields]
    newFields[index] = { ...newFields[index], ...updates }
    setEditForm({ ...editForm, fields: newFields })
  }

  // Add field
  const addField = () => {
    if (!editForm) return
    setEditForm({
      ...editForm,
      fields: [...editForm.fields, { name: '', type: 'string', required: false }],
    })
  }

  // Remove field
  const removeField = (index: number) => {
    if (!editForm) return
    setEditForm({
      ...editForm,
      fields: editForm.fields.filter((_, i) => i !== index),
    })
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-6 h-6 animate-spin text-zinc-400" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-zinc-300">Extraction Schemas</h3>
        {!isCreating && !isEditing && (
          <Button
            variant="outline"
            size="sm"
            onClick={startCreate}
            className="gap-1 h-7 text-xs"
          >
            <Plus className="w-3 h-3" />
            New Schema
          </Button>
        )}
      </div>

      {/* Error message */}
      {error && (
        <div className="text-red-400 bg-red-400/10 rounded-lg p-3 text-sm flex items-start gap-2">
          <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Create/Edit Form */}
      {(isCreating || isEditing) && editForm && (
        <div className="bg-zinc-800 rounded-lg p-4 space-y-4">
          <h4 className="text-sm font-medium text-zinc-200">
            {isCreating ? 'Create New Schema' : 'Edit Schema'}
          </h4>

          {/* Name */}
          <div>
            <label className="block text-xs text-zinc-400 mb-1">Name</label>
            <input
              type="text"
              value={editForm.name}
              onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
              disabled={!!isEditing}
              placeholder="e.g., book_notes"
              className={cn(
                'w-full bg-zinc-700 border border-zinc-600 rounded px-3 py-2 text-sm text-zinc-100',
                'focus:outline-none focus:ring-2 focus:ring-blue-500',
                isEditing && 'opacity-50 cursor-not-allowed'
              )}
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-xs text-zinc-400 mb-1">Description</label>
            <input
              type="text"
              value={editForm.description}
              onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
              placeholder="Describe what this schema extracts"
              className="w-full bg-zinc-700 border border-zinc-600 rounded px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Extraction Hints */}
          <div>
            <label className="block text-xs text-zinc-400 mb-1">
              Extraction Hints (optional)
            </label>
            <textarea
              value={editForm.extraction_hints || ''}
              onChange={(e) =>
                setEditForm({ ...editForm, extraction_hints: e.target.value })
              }
              placeholder="e.g., Look for book titles in headers"
              rows={2}
              className="w-full bg-zinc-700 border border-zinc-600 rounded px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            />
          </div>

          {/* Fields */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs text-zinc-400">Fields</label>
              <Button
                variant="ghost"
                size="sm"
                onClick={addField}
                className="h-6 text-xs gap-1"
              >
                <Plus className="w-3 h-3" />
                Add Field
              </Button>
            </div>
            <div className="space-y-2">
              {editForm.fields.map((field, index) => (
                <div
                  key={index}
                  className="flex items-start gap-2 bg-zinc-700/50 rounded p-2"
                >
                  <div className="flex-1 grid grid-cols-3 gap-2">
                    <input
                      type="text"
                      value={field.name}
                      onChange={(e) => updateField(index, { name: e.target.value })}
                      placeholder="Field name"
                      className="bg-zinc-700 border border-zinc-600 rounded px-2 py-1 text-xs text-zinc-100 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    />
                    <select
                      value={field.type}
                      onChange={(e) =>
                        updateField(index, { type: e.target.value as SchemaField['type'] })
                      }
                      className="bg-zinc-700 border border-zinc-600 rounded px-2 py-1 text-xs text-zinc-100 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    >
                      {FIELD_TYPES.map((type) => (
                        <option key={type} value={type}>
                          {type}
                        </option>
                      ))}
                    </select>
                    <label className="flex items-center gap-1 text-xs text-zinc-400">
                      <input
                        type="checkbox"
                        checked={field.required}
                        onChange={(e) => updateField(index, { required: e.target.checked })}
                        className="rounded"
                      />
                      Required
                    </label>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => removeField(index)}
                    disabled={editForm.fields.length <= 1}
                    className="h-6 w-6 p-0 text-zinc-400 hover:text-red-400"
                  >
                    <X className="w-3 h-3" />
                  </Button>
                </div>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="ghost" size="sm" onClick={cancelEdit} disabled={isSaving}>
              Cancel
            </Button>
            <Button
              variant="default"
              size="sm"
              onClick={saveSchema}
              disabled={isSaving}
              className="gap-1"
            >
              {isSaving ? (
                <>
                  <Loader2 className="w-3 h-3 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Check className="w-3 h-3" />
                  Save
                </>
              )}
            </Button>
          </div>
        </div>
      )}

      {/* Schemas List */}
      {!isCreating && !isEditing && (
        <div className="space-y-2">
          {schemas.length === 0 ? (
            <p className="text-sm text-zinc-500 text-center py-4">
              No schemas defined yet
            </p>
          ) : (
            schemas.map((schema) => (
              <div
                key={schema.name}
                className="bg-zinc-800/50 rounded-lg overflow-hidden"
              >
                {/* Schema header */}
                <button
                  onClick={() => toggleSchema(schema.name)}
                  className="w-full flex items-center justify-between p-3 text-left hover:bg-zinc-700/50 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    {expandedSchema === schema.name ? (
                      <ChevronDown className="w-4 h-4 text-zinc-400" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-zinc-400" />
                    )}
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-zinc-200">
                          {schema.name}
                        </span>
                        {schema.is_builtin && (
                          <span className="text-xs bg-zinc-700 text-zinc-400 px-1.5 py-0.5 rounded">
                            Built-in
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-zinc-500">{schema.description}</p>
                    </div>
                  </div>
                  <span className="text-xs text-zinc-500">
                    {schema.field_count} field{schema.field_count !== 1 ? 's' : ''}
                  </span>
                </button>

                {/* Schema details */}
                {expandedSchema === schema.name && schemaDetails[schema.name] && (
                  <div className="px-3 pb-3 border-t border-zinc-700">
                    <div className="pt-3 space-y-2">
                      {/* Fields */}
                      <div className="text-xs text-zinc-400 mb-1">Fields:</div>
                      <div className="grid grid-cols-2 gap-2">
                        {schemaDetails[schema.name].fields.map((field) => (
                          <div
                            key={field.name}
                            className="flex items-center gap-2 text-xs bg-zinc-700/50 rounded px-2 py-1"
                          >
                            <span className="text-zinc-300">{field.name}</span>
                            <span className="text-zinc-500">{field.type}</span>
                            {field.required && (
                              <span className="text-amber-500">*</span>
                            )}
                          </div>
                        ))}
                      </div>

                      {/* Actions for custom schemas */}
                      {!schema.is_builtin && (
                        <div className="flex justify-end gap-2 pt-2">
                          {deleteConfirm === schema.name ? (
                            <>
                              <span className="text-xs text-red-400 mr-2">
                                Delete this schema?
                              </span>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setDeleteConfirm(null)}
                                className="h-6 text-xs"
                              >
                                Cancel
                              </Button>
                              <Button
                                variant="destructive"
                                size="sm"
                                onClick={() => deleteSchema(schema.name)}
                                className="h-6 text-xs"
                              >
                                Delete
                              </Button>
                            </>
                          ) : (
                            <>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => startEdit(schemaDetails[schema.name])}
                                className="h-6 text-xs gap-1"
                              >
                                <Edit2 className="w-3 h-3" />
                                Edit
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setDeleteConfirm(schema.name)}
                                className="h-6 text-xs gap-1 text-red-400 hover:text-red-300"
                              >
                                <Trash2 className="w-3 h-3" />
                                Delete
                              </Button>
                            </>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}
