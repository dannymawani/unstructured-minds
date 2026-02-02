import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { FileTree } from '../FileTree'
import { FileTreeItem, type FileNode } from '../FileTreeItem'

describe('FileTreeItem', () => {
  const mockFolder: FileNode = {
    path: 'notes',
    name: 'notes',
    isDirectory: true,
    children: [],
  }

  const mockFile: FileNode = {
    path: 'notes/test.md',
    name: 'test.md',
    isDirectory: false,
  }

  it('renders folder with name', () => {
    render(
      <FileTreeItem
        node={mockFolder}
        depth={0}
        expanded={false}
        selected={false}
        onToggle={vi.fn()}
        onSelect={vi.fn()}
      />
    )
    expect(screen.getByText('notes')).toBeInTheDocument()
  })

  it('renders file with name', () => {
    render(
      <FileTreeItem
        node={mockFile}
        depth={0}
        expanded={false}
        selected={false}
        onToggle={vi.fn()}
        onSelect={vi.fn()}
      />
    )
    expect(screen.getByText('test.md')).toBeInTheDocument()
  })

  it('calls onToggle when folder is clicked', () => {
    const onToggle = vi.fn()
    render(
      <FileTreeItem
        node={mockFolder}
        depth={0}
        expanded={false}
        selected={false}
        onToggle={onToggle}
        onSelect={vi.fn()}
      />
    )
    fireEvent.click(screen.getByRole('treeitem'))
    expect(onToggle).toHaveBeenCalledWith('notes')
  })

  it('calls onSelect when file is clicked', () => {
    const onSelect = vi.fn()
    render(
      <FileTreeItem
        node={mockFile}
        depth={0}
        expanded={false}
        selected={false}
        onToggle={vi.fn()}
        onSelect={onSelect}
      />
    )
    fireEvent.click(screen.getByRole('treeitem'))
    expect(onSelect).toHaveBeenCalledWith('notes/test.md')
  })

  it('has selected styling when selected', () => {
    render(
      <FileTreeItem
        node={mockFile}
        depth={0}
        expanded={false}
        selected={true}
        onToggle={vi.fn()}
        onSelect={vi.fn()}
      />
    )
    expect(screen.getByRole('treeitem')).toHaveClass('bg-accent')
  })

  it('has aria-expanded for directories', () => {
    render(
      <FileTreeItem
        node={mockFolder}
        depth={0}
        expanded={true}
        selected={false}
        onToggle={vi.fn()}
        onSelect={vi.fn()}
      />
    )
    expect(screen.getByRole('treeitem')).toHaveAttribute('aria-expanded', 'true')
  })

  it('responds to keyboard Enter', () => {
    const onSelect = vi.fn()
    render(
      <FileTreeItem
        node={mockFile}
        depth={0}
        expanded={false}
        selected={false}
        onToggle={vi.fn()}
        onSelect={onSelect}
      />
    )
    fireEvent.keyDown(screen.getByRole('treeitem'), { key: 'Enter' })
    expect(onSelect).toHaveBeenCalledWith('notes/test.md')
  })
})

describe('FileTree', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('shows loading state initially', () => {
    global.fetch = vi.fn(() => new Promise(() => {}))
    render(<FileTree onFileSelect={vi.fn()} />)
    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })

  it('shows error message on fetch failure', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: false,
        statusText: 'Internal Server Error',
      })
    )
    render(<FileTree onFileSelect={vi.fn()} />)
    await waitFor(() => {
      expect(screen.getByText(/Failed to fetch files/)).toBeInTheDocument()
    })
  })

  it('renders files from API', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            files: [
              { path: 'notes', name: 'notes', is_directory: true },
              { path: 'notes/test.md', name: 'test.md', is_directory: false },
            ],
          }),
      })
    )

    render(<FileTree onFileSelect={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByText('notes')).toBeInTheDocument()
    })
  })

  it('shows empty state when no files', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ files: [] }),
      })
    )

    render(<FileTree onFileSelect={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByText(/No files yet/)).toBeInTheDocument()
    })
  })

  it('expands folder on click', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            files: [
              { path: 'notes', name: 'notes', is_directory: true },
              { path: 'notes/test.md', name: 'test.md', is_directory: false },
            ],
          }),
      })
    )

    render(<FileTree onFileSelect={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByText('notes')).toBeInTheDocument()
    })

    // File should not be visible initially (folder collapsed)
    expect(screen.queryByText('test.md')).not.toBeInTheDocument()

    // Click folder to expand
    fireEvent.click(screen.getByText('notes'))

    // File should now be visible
    expect(screen.getByText('test.md')).toBeInTheDocument()
  })

  it('calls onFileSelect when file is clicked', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            files: [
              { path: 'notes', name: 'notes', is_directory: true },
              { path: 'notes/test.md', name: 'test.md', is_directory: false },
            ],
          }),
      })
    )

    const onFileSelect = vi.fn()
    render(<FileTree onFileSelect={onFileSelect} />)

    await waitFor(() => {
      expect(screen.getByText('notes')).toBeInTheDocument()
    })

    // Expand folder
    fireEvent.click(screen.getByText('notes'))

    // Click file
    fireEvent.click(screen.getByText('test.md'))

    expect(onFileSelect).toHaveBeenCalledWith('notes/test.md')
  })

  it('has new file and folder buttons', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ files: [] }),
      })
    )

    render(<FileTree onFileSelect={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByTitle('New file')).toBeInTheDocument()
      expect(screen.getByTitle('New folder')).toBeInTheDocument()
      expect(screen.getByTitle('Refresh')).toBeInTheDocument()
    })
  })

  it('refreshes files on refresh button click', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ files: [] }),
      })
    )

    render(<FileTree onFileSelect={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByTitle('Refresh')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByTitle('Refresh'))

    expect(global.fetch).toHaveBeenCalledTimes(2)
  })
})
