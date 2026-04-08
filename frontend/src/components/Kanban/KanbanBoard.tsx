import { PersonalKanban } from '../PersonalKanban/PersonalKanban'

interface KanbanBoardProps {
  apiUrl: string
  onFileSelect?: (path: string) => void
}

export function KanbanBoard({ apiUrl, onFileSelect }: KanbanBoardProps) {
  return <PersonalKanban apiUrl={apiUrl} onFileSelect={onFileSelect} />
}
