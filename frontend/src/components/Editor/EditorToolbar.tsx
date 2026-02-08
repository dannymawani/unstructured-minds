import { useInstance } from '@milkdown/react'
import { callCommand } from '@milkdown/utils'
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
import { toggleStrikethroughCommand } from '@milkdown/kit/preset/gfm'

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
    </div>
  )
}
