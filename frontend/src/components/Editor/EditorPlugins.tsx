import { useEffect, useRef } from 'react'
import { useInstance } from '@milkdown/react'
import { SlashProvider, slashFactory } from '@milkdown/kit/plugin/slash'
import { callCommand, $prose } from '@milkdown/utils'
import {
  wrapInHeadingCommand,
  wrapInBulletListCommand,
  wrapInOrderedListCommand,
  wrapInBlockquoteCommand,
  createCodeBlockCommand,
  insertHrCommand,
} from '@milkdown/kit/preset/commonmark'
import { insertTableCommand } from '@milkdown/kit/preset/gfm'
import { editorViewCtx } from '@milkdown/kit/core'
import { keymap } from '@milkdown/prose/keymap'
import { TextSelection } from '@milkdown/prose/state'
import type { EditorView } from '@milkdown/prose/view'
import type { EditorState } from '@milkdown/prose/state'

// ============================================================
// Code Block Exit Plugin
// ============================================================
// Pressing Enter on an empty line at the end of a code block exits it.
// Pressing Mod-Enter anywhere in a code block exits it.

export const codeBlockExitPlugin = $prose(() => {
  return keymap({
    'Enter': (state, dispatch) => {
      const { $head, empty } = state.selection
      if (!empty) return false
      if ($head.parent.type.name !== 'code_block') return false

      const cursorPos = $head.parentOffset
      const text = $head.parent.textContent

      // Only exit if cursor is at the end and the last line is empty
      if (cursorPos !== text.length || !text.endsWith('\n')) return false

      if (dispatch) {
        const posAfterCodeBlock = $head.after()
        const tr = state.tr

        // Remove the trailing empty line
        tr.delete($head.pos - 1, $head.pos)

        // Create a new paragraph after the code block
        const mappedPos = tr.mapping.map(posAfterCodeBlock)
        const paragraph = state.schema.nodes.paragraph.createAndFill()!
        tr.insert(mappedPos, paragraph)

        // Move cursor into the new paragraph
        tr.setSelection(TextSelection.near(tr.doc.resolve(mappedPos + 1)))
        dispatch(tr.scrollIntoView())
      }
      return true
    },

    'Mod-Enter': (state, dispatch) => {
      const { $head, empty } = state.selection
      if (!empty) return false
      if ($head.parent.type.name !== 'code_block') return false

      if (dispatch) {
        const posAfterCodeBlock = $head.after()
        const tr = state.tr

        const paragraph = state.schema.nodes.paragraph.createAndFill()!
        tr.insert(posAfterCodeBlock, paragraph)
        tr.setSelection(TextSelection.near(tr.doc.resolve(posAfterCodeBlock + 1)))
        dispatch(tr.scrollIntoView())
      }
      return true
    },
  })
})

// ============================================================
// Slash Menu Plugin
// ============================================================

/**
 * Insert a task list item by creating a bullet list and setting checked=false.
 * This creates a `- [ ] ` checkbox item in the editor.
 */
export function insertTaskList(editor: any): void {
  // First wrap in bullet list
  editor.action(callCommand(wrapInBulletListCommand.key))
  // Then set checked attribute on the current list_item
  editor.action((ctx: any) => {
    const view = ctx.get(editorViewCtx)
    const { state, dispatch } = view
    const { $head } = state.selection
    // Walk up to find the list_item node
    for (let d = $head.depth; d > 0; d--) {
      const node = $head.node(d)
      if (node.type.name === 'list_item' && node.attrs.checked == null) {
        const pos = $head.before(d)
        dispatch(state.tr.setNodeMarkup(pos, undefined, { ...node.attrs, checked: false }))
        view.focus()
        return true
      }
    }
    return false
  })
}

function createSlashMenuElement(getEditor: () => any, hide: () => void): HTMLElement {
  const el = document.createElement('div')
  el.className = 'slash-menu rounded-md border bg-popover shadow-md p-1 w-56'
  el.style.zIndex = '50'
  el.dataset.show = 'false'

  type SlashItem = {
    label: string
    icon: string
    commandFn?: () => (ctx: any) => boolean
    customFn?: (editor: any) => void
  }

  const items: SlashItem[] = [
    { label: 'Heading 1', icon: 'H1', commandFn: () => callCommand(wrapInHeadingCommand.key, 1) },
    { label: 'Heading 2', icon: 'H2', commandFn: () => callCommand(wrapInHeadingCommand.key, 2) },
    { label: 'Heading 3', icon: 'H3', commandFn: () => callCommand(wrapInHeadingCommand.key, 3) },
    { label: 'Bullet List', icon: '•', commandFn: () => callCommand(wrapInBulletListCommand.key) },
    { label: 'Numbered List', icon: '1.', commandFn: () => callCommand(wrapInOrderedListCommand.key) },
    { label: 'Task List', icon: '☐', customFn: (editor) => insertTaskList(editor) },
    { label: 'Quote', icon: '❞', commandFn: () => callCommand(wrapInBlockquoteCommand.key) },
    { label: 'Code Block', icon: '<>', commandFn: () => callCommand(createCodeBlockCommand.key) },
    { label: 'Divider', icon: '—', commandFn: () => callCommand(insertHrCommand.key) },
    { label: 'Table', icon: '⊞', commandFn: () => callCommand(insertTableCommand.key, { row: 3, col: 3 }) },
  ]

  items.forEach((item) => {
    const btn = document.createElement('button')
    btn.className = 'flex w-full items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-accent cursor-pointer'
    btn.innerHTML = `<span class="w-6 text-center text-xs font-mono text-muted-foreground">${item.icon}</span><span>${item.label}</span>`
    btn.addEventListener('mousedown', (e) => {
      e.preventDefault()
      const editor = getEditor()
      if (editor) {
        if (item.customFn) {
          item.customFn(editor)
        } else if (item.commandFn) {
          editor.action(item.commandFn())
        }
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

