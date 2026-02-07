import { useEffect, useRef } from 'react'
import { useInstance } from '@milkdown/react'
import { SlashProvider, slashFactory } from '@milkdown/kit/plugin/slash'
import { callCommand } from '@milkdown/utils'
import {
  wrapInHeadingCommand,
  wrapInBulletListCommand,
  wrapInOrderedListCommand,
  wrapInBlockquoteCommand,
  createCodeBlockCommand,
  insertHrCommand,
} from '@milkdown/kit/preset/commonmark'
import type { EditorView } from '@milkdown/prose/view'
import type { EditorState } from '@milkdown/prose/state'

// ============================================================
// Slash Menu Plugin
// ============================================================

function createSlashMenuElement(getEditor: () => any, hide: () => void): HTMLElement {
  const el = document.createElement('div')
  el.className = 'slash-menu rounded-md border bg-popover shadow-md p-1 w-56'
  el.style.zIndex = '50'

  const items: { label: string; icon: string; commandFn: () => (ctx: any) => boolean }[] = [
    { label: 'Heading 1', icon: 'H1', commandFn: () => callCommand(wrapInHeadingCommand.key, 1) },
    { label: 'Heading 2', icon: 'H2', commandFn: () => callCommand(wrapInHeadingCommand.key, 2) },
    { label: 'Heading 3', icon: 'H3', commandFn: () => callCommand(wrapInHeadingCommand.key, 3) },
    { label: 'Bullet List', icon: '•', commandFn: () => callCommand(wrapInBulletListCommand.key) },
    { label: 'Numbered List', icon: '1.', commandFn: () => callCommand(wrapInOrderedListCommand.key) },
    { label: 'Quote', icon: '❞', commandFn: () => callCommand(wrapInBlockquoteCommand.key) },
    { label: 'Code Block', icon: '<>', commandFn: () => callCommand(createCodeBlockCommand.key) },
    { label: 'Divider', icon: '—', commandFn: () => callCommand(insertHrCommand.key) },
  ]

  items.forEach((item) => {
    const btn = document.createElement('button')
    btn.className = 'flex w-full items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-accent cursor-pointer'
    btn.innerHTML = `<span class="w-6 text-center text-xs font-mono text-muted-foreground">${item.icon}</span><span>${item.label}</span>`
    btn.addEventListener('mousedown', (e) => {
      e.preventDefault()
      const editor = getEditor()
      if (editor) {
        editor.action(item.commandFn())
      }
      hide()
    })
    el.appendChild(btn)
  })

  return el
}

export const slash = slashFactory('editor-slash')

export function useSlashPlugin() {
  const [loading, getEditor] = useInstance()
  const slashElRef = useRef<HTMLElement | null>(null)
  const providerRef = useRef<SlashProvider | null>(null)

  useEffect(() => {
    if (loading) return

    const editor = getEditor()
    if (!editor) return

    const el = createSlashMenuElement(
      getEditor,
      () => providerRef.current?.hide()
    )
    slashElRef.current = el
    document.body.appendChild(el)

    editor.config((ctx: any) => {
      ctx.set(slash.key, {
        view: (_view: EditorView) => {
          const provider = new SlashProvider({
            content: el,
            debounce: 50,
            offset: { mainAxis: 8, crossAxis: 0 },
          })
          providerRef.current = provider

          return {
            update: (updatedView: EditorView, prevState?: EditorState) => {
              provider.update(updatedView, prevState)
            },
            destroy: () => {
              provider.destroy()
            },
          }
        },
      })
    })

    return () => {
      providerRef.current?.destroy()
      el.remove()
    }
  }, [loading, getEditor])
}

