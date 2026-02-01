import { useEffect, useRef, useCallback } from 'react'
import { Editor, rootCtx, defaultValueCtx } from '@milkdown/kit/core'
import { commonmark } from '@milkdown/kit/preset/commonmark'
import { gfm } from '@milkdown/kit/preset/gfm'
import { history } from '@milkdown/kit/plugin/history'
import { listener, listenerCtx } from '@milkdown/kit/plugin/listener'
import { Milkdown, MilkdownProvider, useEditor } from '@milkdown/react'

interface EditorContentProps {
  content: string
  onChange: (markdown: string) => void
  onSave?: () => void
  autoSaveDelay?: number
}

function EditorContent({
  content,
  onChange,
  onSave,
  autoSaveDelay = 2000,
}: EditorContentProps) {
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const handleChange = useCallback(
    (markdown: string) => {
      onChange(markdown)

      // Auto-save with debounce
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current)
      }

      if (onSave) {
        saveTimeoutRef.current = setTimeout(() => {
          onSave()
        }, autoSaveDelay)
      }
    },
    [onChange, onSave, autoSaveDelay]
  )

  useEditor((root) => {
    return Editor.make()
      .config((ctx) => {
        ctx.set(rootCtx, root)
        ctx.set(defaultValueCtx, content)
      })
      .use(commonmark)
      .use(gfm)
      .use(history)
      .use(listener)
      .config((ctx) => {
        ctx.get(listenerCtx).markdownUpdated((_ctx, markdown) => {
          handleChange(markdown)
        })
      })
  }, [content])

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current)
      }
    }
  }, [])

  return <Milkdown />
}

interface MarkdownEditorProps {
  content: string
  onChange: (markdown: string) => void
  onSave?: () => void
  autoSaveDelay?: number
}

export function MarkdownEditor(props: MarkdownEditorProps) {
  return (
    <div className="milkdown-editor h-full prose prose-sm max-w-none">
      <MilkdownProvider>
        <EditorContent {...props} />
      </MilkdownProvider>
    </div>
  )
}
