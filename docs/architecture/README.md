# Architecture Diagrams

This directory contains Excalidraw diagrams describing the Unstructured Minds system architecture.

## Files

### system-architecture.excalidraw
High-level system architecture showing all major components and their interactions:
- Browser (React 19 + Milkdown + Tailwind)
- Development vs production server layers
- FastAPI backend
- DuckDB database
- Claude API (external)
- Vault filesystem storage
- Docker container boundaries
- Data flow between components

### data-flow.excalidraw
Two complete data pipelines:
- **Extraction pipeline**: Markdown Note → FastAPI → Claude Haiku → DuckDB
- **Query pipeline**: User Question → FastAPI → Claude Sonnet (SQL generation) → DuckDB → Claude Sonnet (formatting) → Answer

### frontend-components.excalidraw
React component tree and views:
- App.tsx with useFileManager and useUIState hooks
- Views: Editor, Dashboard, PersonalKanban, KanbanBoard, Calendar, LifeProfile, DataQuery
- Shared components: FileTree, CommandPalette, DailyNoteWizard, NoteAssist

## Viewing the Diagrams

### Online (Recommended)
1. Go to [excalidraw.com](https://excalidraw.com)
2. Drag and drop a .excalidraw file into the editor
3. Edit and share (files are not uploaded to servers)

### VS Code
1. Install the "Excalidraw" extension
2. Right-click any .excalidraw file and select "Open in Excalidraw"

### Local Excalidraw Instance
```bash
docker run -p 8080:80 excalidraw/excalidraw:latest
# Open http://localhost:8080 and import files
```

## File Format

Files are stored in Excalidraw JSON format (version 2):
- Canvas-based vector drawing format
- Compatible with all Excalidraw tools
- Human-readable JSON for version control
- Colors follow brand guidelines (teal #14b8a6, dark #0f172a, indigo #6366f1, amber #f59e0b, rose #f43f5e)

## Updating Diagrams

When updating diagrams:
1. Make changes in excalidraw.com or VS Code
2. Export as `.excalidraw` file (not PNG or SVG)
3. Commit to version control with clear commit message
4. Reference specific diagrams in documentation with context

## Brand Colors Reference

| Color | Hex | Usage |
|-------|-----|-------|
| Teal (Primary) | #14b8a6 | Core components, data flow, main services |
| Dark | #0f172a | Text, backgrounds, critical systems |
| Indigo | #6366f1 | Links, secondary flows, alternative paths |
| Amber | #f59e0b | Warnings, important notes, highlights |
| Rose | #f43f5e | Errors, external/third-party services |
