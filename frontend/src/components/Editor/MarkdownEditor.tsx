import { useEffect, useRef, useCallback } from 'react'
import { Editor, rootCtx, defaultValueCtx } from '@milkdown/kit/core'
import { commonmark } from '@milkdown/kit/preset/commonmark'
import { gfm } from '@milkdown/kit/preset/gfm'
import { history } from '@milkdown/kit/plugin/history'
import { listener, listenerCtx } from '@milkdown/kit/plugin/listener'
import { Milkdown, MilkdownProvider, useEditor } from '@milkdown/react'
import { slash, tooltip, useSlashPlugin, useTooltipPlugin } from './EditorPlugins'

interface EditorContentProps {
  content: string
  onChange: (markdown: string) => void
  onAutosave?: () => void
  autoSaveDelay?: number
}

function EditorContent({
  content,
  onChange,
  onAutosave,
  autoSaveDelay = 60000,
}: EditorContentProps) {
  const autoSaveIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const isDirtyRef = useRef(false)

  // Start interval-based autosave (disk-only, no extraction)
  useEffect(() => {
    if (!onAutosave) return

    autoSaveIntervalRef.current = setInterval(() => {
      if (isDirtyRef.current) {
        isDirtyRef.current = false
        onAutosave()
      }
    }, autoSaveDelay)

    return () => {
      if (autoSaveIntervalRef.current) {
        clearInterval(autoSaveIntervalRef.current)
      }
    }
  }, [onAutosave, autoSaveDelay])

  const handleChange = useCallback(
    (markdown: string) => {
      onChange(markdown)
      isDirtyRef.current = true
    },
    [onChange]
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
      .use(slash)
      .use(tooltip)
      .config((ctx) => {
        ctx.get(listenerCtx).markdownUpdated((_ctx, markdown) => {
          handleChange(markdown)
        })
      })
  }, [content])

  useSlashPlugin()
  useTooltipPlugin()

  // Flush unsaved content on unmount
  useEffect(() => {
    return () => {
      if (isDirtyRef.current && onAutosave) {
        onAutosave()
      }
    }
  }, [onAutosave])

  return <Milkdown />
}

interface MarkdownEditorProps {
  content: string
  onChange: (markdown: string) => void
  onAutosave?: () => void
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
