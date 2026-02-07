import { useState, useCallback, useRef, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router'
import { api } from '@/lib/apiClient'

export function useFileManager() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  const [selectedFile, setSelectedFile] = useState<string | undefined>()
  const [content, setContent] = useState('')
  const contentRef = useRef(content)
  const [saveState, setSaveState] = useState<'idle' | 'saving' | 'extracting' | 'saved'>('idle')
  const isDirtyRef = useRef(false)

  const fetchFileContent = useCallback(async (path: string) => {
    try {
      const data = await api.get<{ content: string }>(
        `/vault/file?path=${encodeURIComponent(path)}`
      )
      return data.content
    } catch (err) {
      console.error('Error loading file:', err)
      return ''
    }
  }, [])

  const handleFileSelect = useCallback(
    async (path: string) => {
      const fileContent = await fetchFileContent(path)
      setContent(fileContent)
      contentRef.current = fileContent
      isDirtyRef.current = false
      setSelectedFile(path)
      navigate(`/editor?file=${encodeURIComponent(path)}`)
    },
    [fetchFileContent, navigate]
  )

  const handleContentChange = useCallback((markdown: string) => {
    setContent(markdown)
    contentRef.current = markdown
    isDirtyRef.current = true
  }, [])

  const handleNoteContentUpdate = useCallback((newContent: string) => {
    setContent(newContent)
    contentRef.current = newContent
    isDirtyRef.current = true

    if (selectedFile) {
      api.post(`/vault/file?extract=false`, { path: selectedFile, content: newContent })
        .then(() => { isDirtyRef.current = false })
        .catch((err) => console.error('Error saving note-assist update:', err))
    }
  }, [selectedFile])

  const handleAutosave = useCallback(async () => {
    if (!selectedFile) return

    setSaveState('saving')
    try {
      await api.post(`/vault/file?extract=false`, { path: selectedFile, content: contentRef.current })
      isDirtyRef.current = false
      setSaveState('saved')
      setTimeout(() => setSaveState('idle'), 2000)
    } catch (err) {
      console.error('Error saving file:', err)
      setSaveState('idle')
    }
  }, [selectedFile])

  const handleSave = useCallback(async () => {
    if (!selectedFile) return

    setSaveState('extracting')
    try {
      await api.post(`/vault/file?extract=true`, { path: selectedFile, content: contentRef.current })
      isDirtyRef.current = false
      setSaveState('saved')
      setTimeout(() => setSaveState('idle'), 2000)
    } catch (err) {
      console.error('Error saving file:', err)
      setSaveState('idle')
    }
  }, [selectedFile])

  // Extract on file switch if dirty
  const prevFileRef = useRef<string | undefined>(selectedFile)
  useEffect(() => {
    if (prevFileRef.current && prevFileRef.current !== selectedFile && isDirtyRef.current) {
      const prevFile = prevFileRef.current
      api.post(`/vault/file?extract=true`, { path: prevFile, content: contentRef.current })
        .catch((err) => console.error('Error saving on file switch:', err))
      isDirtyRef.current = false
    }
    prevFileRef.current = selectedFile
  }, [selectedFile])

  // Deep link: load file from ?file= query param
  const fileParam = searchParams.get('file')
  useEffect(() => {
    if (fileParam && fileParam !== selectedFile) {
      fetchFileContent(fileParam).then((fileContent) => {
        setContent(fileContent)
        contentRef.current = fileContent
        isDirtyRef.current = false
        setSelectedFile(fileParam)
      })
    }
  }, [fileParam, selectedFile, fetchFileContent])

  const handleDeleteFile = useCallback(
    (path: string) => {
      if (selectedFile === path) {
        setSelectedFile(undefined)
        setContent('')
        contentRef.current = ''
        isDirtyRef.current = false
        navigate('/editor')
      }
    },
    [selectedFile, navigate]
  )

  const handleRenameFile = useCallback(
    (oldPath: string, newPath: string) => {
      if (selectedFile === oldPath) {
        setSelectedFile(newPath)
        navigate(`/editor?file=${encodeURIComponent(newPath)}`)
      }
    },
    [selectedFile, navigate]
  )

  return {
    selectedFile,
    setSelectedFile,
    content,
    setContent,
    contentRef,
    isDirtyRef,
    saveState,
    fetchFileContent,
    handleFileSelect,
    handleContentChange,
    handleNoteContentUpdate,
    handleAutosave,
    handleSave,
    handleDeleteFile,
    handleRenameFile,
  }
}
