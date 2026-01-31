---
name: frontend-patterns
description: React and Milkdown patterns for the web frontend. Use when implementing or reviewing frontend code.
user-invocable: false
---

# Frontend Patterns

Standards for the Unstructured Minds React + Milkdown web frontend (Docker).

## Component Structure

```typescript
// src/components/Editor/Editor.tsx
import { Editor, rootCtx, defaultValueCtx } from '@milkdown/core'
import { commonmark } from '@milkdown/preset-commonmark'
import { nord } from '@milkdown/theme-nord'
import { ReactEditor, useEditor } from '@milkdown/react'
import { listener, listenerCtx } from '@milkdown/plugin-listener'

interface EditorProps {
  content: string
  onUpdate: (content: string) => void
  readOnly?: boolean
}

export function MarkdownEditor({ content, onUpdate, readOnly = false }: EditorProps) {
  const { editor } = useEditor((root) =>
    Editor.make()
      .config((ctx) => {
        ctx.set(rootCtx, root)
        ctx.set(defaultValueCtx, content)
        ctx.get(listenerCtx).markdownUpdated((_, markdown) => {
          onUpdate(markdown)
        })
      })
      .use(nord)
      .use(commonmark)
      .use(listener)
  )

  return <ReactEditor editor={editor} />
}
```

## State Management (Zustand)

```typescript
// src/stores/noteStore.ts
import { create } from 'zustand'

interface Note {
  id: string
  title: string
  content: string
  date: string
}

interface NoteStore {
  notes: Note[]
  currentNote: Note | null
  setCurrentNote: (note: Note | null) => void
  updateNote: (id: string, updates: Partial<Note>) => void
}

export const useNoteStore = create<NoteStore>((set) => ({
  notes: [],
  currentNote: null,
  setCurrentNote: (note) => set({ currentNote: note }),
  updateNote: (id, updates) =>
    set((state) => ({
      notes: state.notes.map((n) =>
        n.id === id ? { ...n, ...updates } : n
      ),
    })),
}))
```

## API Calls

```typescript
// src/hooks/useApi.ts
import { useState, useCallback } from 'react'

const API_BASE = 'http://localhost:8000/api/v1'

export function useApi<T>() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  const request = useCallback(async (
    endpoint: string,
    options?: RequestInit
  ): Promise<T> => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options?.headers,
        },
      })
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`)
      }
      return await response.json()
    } catch (e) {
      setError(e as Error)
      throw e
    } finally {
      setLoading(false)
    }
  }, [])

  return { request, loading, error }
}
```

## File Naming

- Components: `PascalCase.tsx` (e.g., `NoteEditor.tsx`)
- Hooks: `useCamelCase.ts` (e.g., `useNoteStore.ts`)
- Utils: `camelCase.ts` (e.g., `dateUtils.ts`)
- Types: `types.ts` or `*.types.ts`
