import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock @tanstack/react-virtual to avoid jsdom/memory issues
vi.mock('@tanstack/react-virtual', () => ({
  useVirtualizer: ({ count, getScrollElement, estimateSize }: any) => ({
    getVirtualItems: () =>
      Array.from({ length: count }, (_, i) => ({
        index: i,
        start: i * (estimateSize?.() ?? 28),
        size: estimateSize?.() ?? 28,
        key: i,
      })),
    getTotalSize: () => count * (estimateSize?.() ?? 28),
  }),
}))

import { FileTree, transformDailyNotes } from '../FileTree'
import { FileTreeItem, type FileNode } from '../FileTreeItem'
import { buildTree } from '../treeUtils'

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
    // Use a promise that will eventually resolve to avoid memory leaks
    let resolvePromise: (value: any) => void
    global.fetch = vi.fn(
      () =>
        new Promise((resolve) => {
          resolvePromise = resolve
        })
    )
    const { unmount } = render(<FileTree onFileSelect={vi.fn()} />)
    expect(screen.getByText('Loading...')).toBeInTheDocument()
    unmount()
    // Resolve the dangling promise to prevent leak
    resolvePromise!({ ok: true, json: () => Promise.resolve({ files: [] }) })
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
      expect(screen.getByTitle('New note')).toBeInTheDocument()
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

    // 3 calls: mount settings fetch + mount file fetch + refresh file fetch
    expect(global.fetch).toHaveBeenCalledTimes(3)
  })
})

describe('transformDailyNotes', () => {
  function makeDailyNotesTree(): FileNode[] {
    return [
      {
        path: 'Daily-Notes',
        name: 'Daily-Notes',
        isDirectory: true,
        children: [
          {
            path: 'Daily-Notes/Life-Profile.md',
            name: 'Life-Profile.md',
            isDirectory: false,
          },
          {
            path: 'Daily-Notes/2026-02',
            name: '2026-02',
            isDirectory: true,
            children: [
              { path: 'Daily-Notes/2026-02/2026-02-07.md', name: '2026-02-07.md', isDirectory: false },
            ],
          },
          {
            path: 'Daily-Notes/2026-01',
            name: '2026-01',
            isDirectory: true,
            children: [
              { path: 'Daily-Notes/2026-01/2026-01-15.md', name: '2026-01-15.md', isDirectory: false },
            ],
          },
          {
            path: 'Daily-Notes/2025-12',
            name: '2025-12',
            isDirectory: true,
            children: [
              { path: 'Daily-Notes/2025-12/2025-12-25.md', name: '2025-12-25.md', isDirectory: false },
            ],
          },
        ],
      },
      {
        path: 'Templates',
        name: 'Templates',
        isDirectory: true,
        children: [],
      },
    ]
  }

  it('groups month folders under virtual year nodes', () => {
    const result = transformDailyNotes(makeDailyNotesTree())
    const dailyNotes = result.find((n) => n.path === 'Daily-Notes')!

    // Should have: Life-Profile.md, 2026 year node, 2025 year node
    expect(dailyNotes.children).toHaveLength(3)

    const yearNode2026 = dailyNotes.children!.find((n) => n.name === '2026')!
    expect(yearNode2026).toBeDefined()
    expect(yearNode2026.isVirtual).toBe(true)
    expect(yearNode2026.path).toBe('Daily-Notes/__year__/2026')
    expect(yearNode2026.children).toHaveLength(2) // February, January
  })

  it('uses human-readable month names as displayName', () => {
    const result = transformDailyNotes(makeDailyNotesTree(), true)
    const dailyNotes = result.find((n) => n.path === 'Daily-Notes')!
    const yearNode2026 = dailyNotes.children!.find((n) => n.name === '2026')!

    const feb = yearNode2026.children!.find((n) => n.path === 'Daily-Notes/2026-02')!
    const jan = yearNode2026.children!.find((n) => n.path === 'Daily-Notes/2026-01')!

    expect(feb.displayName).toBe('February')
    expect(jan.displayName).toBe('January')
  })

  it('keeps non-month files as direct children of Daily-Notes', () => {
    const result = transformDailyNotes(makeDailyNotesTree())
    const dailyNotes = result.find((n) => n.path === 'Daily-Notes')!

    const lifeProfile = dailyNotes.children!.find((n) => n.name === 'Life-Profile.md')
    expect(lifeProfile).toBeDefined()
    expect(lifeProfile!.isDirectory).toBe(false)
  })

  it('sorts years newest first, months newest first', () => {
    const result = transformDailyNotes(makeDailyNotesTree(), true)
    const dailyNotes = result.find((n) => n.path === 'Daily-Notes')!

    // Non-month children come first, then year nodes newest-first
    const dirChildren = dailyNotes.children!.filter((n) => n.isDirectory)
    expect(dirChildren[0].name).toBe('2026')
    expect(dirChildren[1].name).toBe('2025')

    // Within 2026, February before January
    const yearNode2026 = dirChildren[0]
    expect(yearNode2026.children![0].displayName).toBe('February')
    expect(yearNode2026.children![1].displayName).toBe('January')
  })

  it('does not modify trees without Daily-Notes', () => {
    const roots: FileNode[] = [
      { path: 'Templates', name: 'Templates', isDirectory: true, children: [] },
    ]
    const result = transformDailyNotes(roots)
    expect(result).toEqual(roots)
  })

  it('preserves month folder children (daily note files)', () => {
    const result = transformDailyNotes(makeDailyNotesTree())
    const dailyNotes = result.find((n) => n.path === 'Daily-Notes')!
    const yearNode2026 = dailyNotes.children!.find((n) => n.name === '2026')!
    const feb = yearNode2026.children!.find((n) => n.path === 'Daily-Notes/2026-02')!

    expect(feb.children).toHaveLength(1)
    expect(feb.children![0].name).toBe('2026-02-07.md')
  })
})
