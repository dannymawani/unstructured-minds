import { render, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { MarkdownEditor } from '../MarkdownEditor'

describe('MarkdownEditor', () => {
  it('renders editor container', () => {
    const { container } = render(
      <MarkdownEditor content="# Hello" onChange={() => {}} />
    )
    expect(container.querySelector('.milkdown-editor')).toBeInTheDocument()
  })

  it('renders milkdown component', async () => {
    const { container } = render(
      <MarkdownEditor content="# Test" onChange={() => {}} />
    )

    // Milkdown creates a .milkdown class element
    await waitFor(
      () => {
        expect(container.querySelector('.milkdown')).toBeInTheDocument()
      },
      { timeout: 3000 }
    )
  })

  it('renders initial content', async () => {
    const { container } = render(
      <MarkdownEditor content="# Hello World" onChange={() => {}} />
    )

    await waitFor(
      () => {
        const editor = container.querySelector('.ProseMirror')
        expect(editor).toBeInTheDocument()
        expect(editor?.textContent).toContain('Hello World')
      },
      { timeout: 3000 }
    )
  })

  it('accepts onChange prop', () => {
    const onChange = vi.fn()
    const { container } = render(
      <MarkdownEditor content="# Test" onChange={onChange} />
    )
    expect(container.querySelector('.milkdown-editor')).toBeInTheDocument()
  })

  it('accepts onSave prop for auto-save', () => {
    const onSave = vi.fn()
    const onChange = vi.fn()

    const { container } = render(
      <MarkdownEditor
        content="# Test"
        onChange={onChange}
        onSave={onSave}
        autoSaveDelay={100}
      />
    )
    expect(container.querySelector('.milkdown-editor')).toBeInTheDocument()
  })
})
