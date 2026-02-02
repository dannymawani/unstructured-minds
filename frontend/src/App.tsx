import { useState, useCallback, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { FileTree } from '@/components/FileTree'
import { MarkdownEditor } from '@/components/Editor/MarkdownEditor'
import { ChatPanel } from '@/components/Chat'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function App() {
  const [selectedFile, setSelectedFile] = useState<string | undefined>()
  const [content, setContent] = useState('')
  const [isSaving, setIsSaving] = useState(false)

  const fetchFileContent = useCallback(async (path: string) => {
    try {
      const response = await fetch(
        `${API_BASE_URL}/vault/file?path=${encodeURIComponent(path)}`
      )
      if (!response.ok) {
        throw new Error('Failed to fetch file')
      }
      const data = await response.json()
      setContent(data.content)
    } catch (err) {
      console.error('Error loading file:', err)
      setContent('')
    }
  }, [])

  const handleFileSelect = useCallback(
    (path: string) => {
      setSelectedFile(path)
      fetchFileContent(path)
    },
    [fetchFileContent]
  )

  const handleContentChange = useCallback((markdown: string) => {
    setContent(markdown)
  }, [])

  const handleSave = useCallback(async () => {
    if (!selectedFile) return

    setIsSaving(true)
    try {
      const response = await fetch(`${API_BASE_URL}/vault/file`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: selectedFile, content }),
      })
      if (!response.ok) {
        throw new Error('Failed to save file')
      }
    } catch (err) {
      console.error('Error saving file:', err)
    } finally {
      setIsSaving(false)
    }
  }, [selectedFile, content])

  // Keyboard shortcut for save
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
        e.preventDefault()
        handleSave()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleSave])

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="border-b px-4 py-3 flex items-center justify-between">
        <h1 className="text-lg font-semibold">Unstructured Minds</h1>
        <div className="flex items-center gap-2">
          {isSaving && (
            <span className="text-sm text-muted-foreground">Saving...</span>
          )}
          <Button variant="outline" size="sm">
            Settings
          </Button>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 flex overflow-hidden">
        {/* File browser sidebar */}
        <aside className="w-64 border-r">
          <FileTree
            onFileSelect={handleFileSelect}
            selectedFile={selectedFile}
            apiBaseUrl={API_BASE_URL}
          />
        </aside>

        {/* Editor */}
        <section className="flex-1 overflow-auto">
          {selectedFile ? (
            <div className="h-full p-4">
              <MarkdownEditor
                content={content}
                onChange={handleContentChange}
                onSave={handleSave}
              />
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              <p>Select a file to start editing</p>
            </div>
          )}
        </section>

        {/* Chat panel */}
        <aside className="w-80 border-l">
          <ChatPanel apiBaseUrl={API_BASE_URL} />
        </aside>
      </main>
    </div>
  )
}

export default App
