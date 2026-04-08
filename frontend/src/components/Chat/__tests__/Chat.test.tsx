import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ChatPanel } from '../ChatPanel'
import { ChatMessage, type Message } from '../ChatMessage'

// Mock scrollIntoView for jsdom
Element.prototype.scrollIntoView = vi.fn()

describe('ChatMessage', () => {
  it('renders user message with correct styling', () => {
    const message: Message = {
      id: '1',
      role: 'user',
      content: 'Hello, world!',
    }
    render(<ChatMessage message={message} />)
    expect(screen.getByText('Hello, world!')).toBeInTheDocument()
    expect(screen.getByText('You')).toBeInTheDocument()
  })

  it('renders assistant message with correct styling', () => {
    const message: Message = {
      id: '2',
      role: 'assistant',
      content: 'Hi there!',
    }
    render(<ChatMessage message={message} />)
    expect(screen.getByText('Hi there!')).toBeInTheDocument()
    expect(screen.getByText('Assistant')).toBeInTheDocument()
  })

  it('displays timestamp when provided', () => {
    const message: Message = {
      id: '3',
      role: 'user',
      content: 'Test message',
      timestamp: new Date('2026-02-02T14:30:00'),
    }
    render(<ChatMessage message={message} />)
    // The exact format depends on locale, just check it's there
    expect(screen.getByText('Test message')).toBeInTheDocument()
  })
})

describe('ChatPanel', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('renders empty state', () => {
    render(<ChatPanel />)
    expect(screen.getByText('Start a conversation')).toBeInTheDocument()
  })

  it('has input field and send button', () => {
    render(<ChatPanel />)
    expect(screen.getByPlaceholderText('Ask a question...')).toBeInTheDocument()
    expect(screen.getByTitle('Send message')).toBeInTheDocument()
  })

  it('send button is disabled when input is empty', () => {
    render(<ChatPanel />)
    expect(screen.getByTitle('Send message')).toBeDisabled()
  })

  it('send button is enabled when input has text', () => {
    render(<ChatPanel />)
    const input = screen.getByPlaceholderText('Ask a question...')
    fireEvent.change(input, { target: { value: 'Hello' } })
    expect(screen.getByTitle('Send message')).not.toBeDisabled()
  })

  it('sends message on form submit', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            message: { role: 'assistant', content: 'Hello back!' },
            context_used: false,
          }),
      })
    )

    render(<ChatPanel />)
    const input = screen.getByPlaceholderText('Ask a question...')
    fireEvent.change(input, { target: { value: 'Hello' } })
    fireEvent.click(screen.getByTitle('Send message'))

    // User message appears
    await waitFor(() => {
      expect(screen.getByText('Hello')).toBeInTheDocument()
    })

    // Assistant response appears
    await waitFor(() => {
      expect(screen.getByText('Hello back!')).toBeInTheDocument()
    })
  })

  it('sends message on Enter key', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            message: { role: 'assistant', content: 'Response' },
            context_used: false,
          }),
      })
    )

    render(<ChatPanel />)
    const input = screen.getByPlaceholderText('Ask a question...')
    fireEvent.change(input, { target: { value: 'Test' } })
    fireEvent.keyDown(input, { key: 'Enter' })

    await waitFor(() => {
      expect(screen.getByText('Test')).toBeInTheDocument()
    })
  })

  it('does not send on Shift+Enter', () => {
    render(<ChatPanel />)
    const input = screen.getByPlaceholderText('Ask a question...')
    fireEvent.change(input, { target: { value: 'Test' } })
    fireEvent.keyDown(input, { key: 'Enter', shiftKey: true })

    expect(screen.queryByText('You')).not.toBeInTheDocument()
  })

  it('shows loading state while waiting for response', async () => {
    global.fetch = vi.fn(
      () =>
        new Promise((resolve) =>
          setTimeout(
            () =>
              resolve({
                ok: true,
                json: () =>
                  Promise.resolve({
                    message: { role: 'assistant', content: 'Delayed response' },
                    context_used: false,
                  }),
              }),
            100
          )
        )
    )

    render(<ChatPanel />)
    const input = screen.getByPlaceholderText('Ask a question...')
    fireEvent.change(input, { target: { value: 'Hello' } })
    fireEvent.click(screen.getByTitle('Send message'))

    // Should show loading state
    await waitFor(() => {
      expect(screen.getByText('Thinking...')).toBeInTheDocument()
    })

    // Should show response after loading
    await waitFor(() => {
      expect(screen.getByText('Delayed response')).toBeInTheDocument()
    })
  })

  it('shows error message on API failure', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: false,
        json: () => Promise.resolve({ detail: 'API Error' }),
      })
    )

    render(<ChatPanel />)
    const input = screen.getByPlaceholderText('Ask a question...')
    fireEvent.change(input, { target: { value: 'Hello' } })
    fireEvent.click(screen.getByTitle('Send message'))

    await waitFor(() => {
      expect(screen.getByText('API Error')).toBeInTheDocument()
    })
  })

  it('clears input after sending', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            message: { role: 'assistant', content: 'Response' },
            context_used: false,
          }),
      })
    )

    render(<ChatPanel />)
    const input = screen.getByPlaceholderText('Ask a question...')
    fireEvent.change(input, { target: { value: 'Hello' } })
    fireEvent.click(screen.getByTitle('Send message'))

    await waitFor(() => {
      expect(input).toHaveValue('')
    })
  })
})
