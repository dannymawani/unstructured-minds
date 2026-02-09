import { useState, useRef, useEffect, useCallback } from 'react'
import { useInstance } from '@milkdown/react'
import { callCommand } from '@milkdown/utils'
import { editorViewCtx } from '@milkdown/kit/core'
import {
  toggleStrongCommand,
  toggleEmphasisCommand,
  toggleInlineCodeCommand,
  wrapInHeadingCommand,
  wrapInBulletListCommand,
  wrapInOrderedListCommand,
  wrapInBlockquoteCommand,
  createCodeBlockCommand,
  insertHrCommand,
} from '@milkdown/kit/preset/commonmark'
import { toggleStrikethroughCommand, insertTableCommand } from '@milkdown/kit/preset/gfm'
import { isInTable, addRowAfter, addColumnAfter, deleteRow, deleteColumn, deleteTable } from '@milkdown/prose/tables'
import { Table2, Plus, Minus, Trash2, Rows3, Columns3 } from 'lucide-react'

function ToolbarButton({
  label,
  title,
  onAction,
}: {
  label: string
  title: string
  onAction: () => void
}) {
  return (
    <button
      className="toolbar-btn"
      title={title}
      onMouseDown={(e) => {
        e.preventDefault()
        onAction()
      }}
      dangerouslySetInnerHTML={{ __html: label }}
    />
  )
}

function Divider() {
  return <div className="toolbar-divider" />
}

const GRID_ROWS = 6
const GRID_COLS = 6

function TableInsertButton({ runCommand }: { runCommand: (command: any, payload?: any) => void }) {
  const [open, setOpen] = useState(false)
  const [hoverRow, setHoverRow] = useState(0)
  const [hoverCol, setHoverCol] = useState(0)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [open])

  return (
    <div className="table-insert-container" ref={containerRef}>
      <button
        className="toolbar-btn"
        title="Insert Table"
        onMouseDown={(e) => {
          e.preventDefault()
          setOpen(!open)
        }}
      >
        <Table2 size={14} />
      </button>
      {open && (
        <div className="table-grid-picker" onMouseDown={(e) => e.preventDefault()}>
          <div className="table-grid-label">
            {hoverRow > 0 ? `${hoverRow} × ${hoverCol}` : 'Select size'}
          </div>
          <div className="table-grid">
            {Array.from({ length: GRID_ROWS }, (_, r) => (
              <div className="table-grid-row" key={r}>
                {Array.from({ length: GRID_COLS }, (_, c) => (
                  <div
                    key={c}
                    className={`table-grid-cell${r < hoverRow && c < hoverCol ? ' highlighted' : ''}`}
                    onMouseEnter={() => { setHoverRow(r + 1); setHoverCol(c + 1) }}
                    onMouseDown={(e) => {
                      e.preventDefault()
                      runCommand(insertTableCommand.key, { row: r + 1, col: c + 1 })
                      setOpen(false)
                      setHoverRow(0)
                      setHoverCol(0)
                    }}
                  />
                ))}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function TableEditButtons({ getEditor, loading }: { getEditor: () => any; loading: boolean }) {
  const [inTable, setInTable] = useState(false)

  useEffect(() => {
    if (loading) return
    const check = () => {
      const editor = getEditor()
      if (!editor) return
      try {
        editor.action((ctx: any) => {
          const view = ctx.get(editorViewCtx)
          setInTable(isInTable(view.state))
        })
      } catch {
        setInTable(false)
      }
    }
    // Check on an interval since ProseMirror state changes don't trigger React re-renders
    check()
    const id = setInterval(check, 300)
    return () => clearInterval(id)
  }, [loading, getEditor])

  const runProse = useCallback((cmd: (state: any, dispatch?: any) => boolean) => {
    if (loading) return
    const editor = getEditor()
    if (!editor) return
    editor.action((ctx: any) => {
      const view = ctx.get(editorViewCtx)
      cmd(view.state, view.dispatch)
      view.focus()
    })
  }, [loading, getEditor])

  if (!inTable) return null

  return (
    <>
      <Divider />
      <button
        className="toolbar-btn"
        title="Add Row"
        onMouseDown={(e) => { e.preventDefault(); runProse(addRowAfter) }}
      >
        <Rows3 size={14} />
        <Plus size={8} className="toolbar-btn-badge" />
      </button>
      <button
        className="toolbar-btn"
        title="Add Column"
        onMouseDown={(e) => { e.preventDefault(); runProse(addColumnAfter) }}
      >
        <Columns3 size={14} />
        <Plus size={8} className="toolbar-btn-badge" />
      </button>
      <button
        className="toolbar-btn"
        title="Delete Row"
        onMouseDown={(e) => { e.preventDefault(); runProse(deleteRow) }}
      >
        <Rows3 size={14} />
        <Minus size={8} className="toolbar-btn-badge" />
      </button>
      <button
        className="toolbar-btn"
        title="Delete Column"
        onMouseDown={(e) => { e.preventDefault(); runProse(deleteColumn) }}
      >
        <Columns3 size={14} />
        <Minus size={8} className="toolbar-btn-badge" />
      </button>
      <button
        className="toolbar-btn toolbar-btn-danger"
        title="Delete Table"
        onMouseDown={(e) => { e.preventDefault(); runProse(deleteTable) }}
      >
        <Trash2 size={14} />
      </button>
    </>
  )
}

export function EditorToolbar() {
  const [loading, getEditor] = useInstance()

  const runCommand = (command: Parameters<typeof callCommand>[0], payload?: any) => {
    if (loading) return
    const editor = getEditor()
    if (editor) {
      editor.action(callCommand(command, payload))
    }
  }

  return (
    <div className="editor-toolbar">
      {/* Inline formatting */}
      <ToolbarButton label="<b>B</b>" title="Bold" onAction={() => runCommand(toggleStrongCommand.key)} />
      <ToolbarButton label="<i>I</i>" title="Italic" onAction={() => runCommand(toggleEmphasisCommand.key)} />
      <ToolbarButton label="<s>S</s>" title="Strikethrough" onAction={() => runCommand(toggleStrikethroughCommand.key)} />
      <ToolbarButton label="<code>&lt;&gt;</code>" title="Inline Code" onAction={() => runCommand(toggleInlineCodeCommand.key)} />

      <Divider />

      {/* Headings */}
      <ToolbarButton label="H1" title="Heading 1" onAction={() => runCommand(wrapInHeadingCommand.key, 1)} />
      <ToolbarButton label="H2" title="Heading 2" onAction={() => runCommand(wrapInHeadingCommand.key, 2)} />
      <ToolbarButton label="H3" title="Heading 3" onAction={() => runCommand(wrapInHeadingCommand.key, 3)} />

      <Divider />

      {/* Lists */}
      <ToolbarButton label="&bull;" title="Bullet List" onAction={() => runCommand(wrapInBulletListCommand.key)} />
      <ToolbarButton label="1." title="Numbered List" onAction={() => runCommand(wrapInOrderedListCommand.key)} />

      <Divider />

      {/* Block elements */}
      <ToolbarButton label="&#10078;" title="Quote" onAction={() => runCommand(wrapInBlockquoteCommand.key)} />
      <ToolbarButton label="&#123;&#125;" title="Code Block" onAction={() => runCommand(createCodeBlockCommand.key)} />
      <ToolbarButton label="&mdash;" title="Divider" onAction={() => runCommand(insertHrCommand.key)} />

      <Divider />

      {/* Table */}
      <TableInsertButton runCommand={runCommand} />

      {/* Table edit controls — only visible when cursor is in a table */}
      <TableEditButtons getEditor={getEditor} loading={loading} />
    </div>
  )
}
