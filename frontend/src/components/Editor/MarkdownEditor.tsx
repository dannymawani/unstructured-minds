import { useEffect, useRef } from 'react'
import { Editor, rootCtx, defaultValueCtx } from '@milkdown/kit/core'
import { commonmark } from '@milkdown/kit/preset/commonmark'
import { gfm } from '@milkdown/kit/preset/gfm'
import { history } from '@milkdown/kit/plugin/history'
import { listener, listenerCtx } from '@milkdown/kit/plugin/listener'
import { tableBlock, tableBlockConfig } from '@milkdown/kit/component/table-block'
import { Milkdown, MilkdownProvider, useEditor } from '@milkdown/react'
import { slash, useSlashPlugin, codeBlockExitPlugin } from './EditorPlugins'
import { EditorToolbar } from './EditorToolbar'

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
  // Capture initial content so useEditor doesn't re-create on every keystroke
  const initialContentRef = useRef(content)
  const onChangeRef = useRef(onChange)
  onChangeRef.current = onChange

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

  useEditor((root) => {
    return Editor.make()
      .config((ctx) => {
        ctx.set(rootCtx, root)
        ctx.set(defaultValueCtx, initialContentRef.current)
      })
      .use(commonmark)
      .use(gfm)
      .use(tableBlock)
      .use(history)
      .use(listener)
      .use(slash)
      .use(codeBlockExitPlugin)
      .config((ctx) => {
        ctx.update(tableBlockConfig.key, (defaultConfig) => ({
          ...defaultConfig,
          renderButton: (renderType: string) => {
            switch (renderType) {
              case 'add_row': return '+'
              case 'add_col': return '+'
              case 'delete_row': return '×'
              case 'delete_col': return '×'
              case 'align_col_left': return '←'
              case 'align_col_center': return '↔'
              case 'align_col_right': return '→'
              case 'col_drag_handle': return '⠿'
              case 'row_drag_handle': return '⠿'
              default: return ''
            }
          },
        }))
        ctx.get(listenerCtx).markdownUpdated((_ctx, markdown) => {
          onChangeRef.current(markdown)
          isDirtyRef.current = true
        })
      })
  }, [])

  useSlashPlugin()

  // Flush unsaved content on unmount
  useEffect(() => {
    return () => {
      if (isDirtyRef.current && onAutosave) {
        onAutosave()
      }
    }
  }, [onAutosave])

  return (
    <>
      <EditorToolbar />
      <Milkdown />
    </>
  )
}

interface MarkdownEditorProps {
  content: string
  onChange: (markdown: string) => void
  onAutosave?: () => void
  autoSaveDelay?: number
}

export function MarkdownEditor(props: MarkdownEditorProps) {
  return (
    <div className="milkdown-editor min-h-full max-w-none bg-card">
      <MilkdownProvider>
        <EditorContent {...props} />
      </MilkdownProvider>
    </div>
  )
}
