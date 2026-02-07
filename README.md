# Unstructured Minds

> Your second brain with a SQL engine underneath.

A containerized web application that transforms natural language notes into structured, queryable data. Write naturally in markdown, and let AI extract insights into a personal data warehouse.

---

## What is this?

**Unstructured Minds** bridges the gap between free-form note-taking and structured data:

```
"Had oatmeal for breakfast, then hit the gym for squats 100kg 3x5"
                              ↓
                     Claude extracts data
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  food_log: breakfast, oatmeal                                   │
│  exercise_log: squat, 100kg, 5 reps, 3 sets                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
            "How many times did I squat over 100kg this month?"
                              ↓
                         Answer: 6 days
```

## Features

| Feature | Description |
|---------|-------------|
| **Markdown Editor** | Milkdown-powered WYSIWYG editing with toolbar, templates, and raw toggle |
| **Natural Language Logging** | Write freely, AI extracts structured data into DuckDB |
| **AI-Powered Queries** | Ask questions in plain English, get SQL-backed answers |
| **Daily Note Wizard** | One-click daily notes with structured creation wizard |
| **Dashboards** | Activity heatmaps, exercise progress, sleep trends, mood correlations |
| **Personal Kanban** | Drag-and-drop task board synced with daily note checkboxes |
| **Calendar View** | Visual calendar with daily note navigation |
| **Life Profile** | Goals, training history, and progress reviews |
| **Note Assistant** | AI chat for editing notes with image support |
| **Full-Text Search** | Search across all vault notes with snippets and scoring |
| **Command Palette** | Cmd+K for quick actions |
| **Local-First** | All data stays on your machine in DuckDB |

## Tech Stack

| Layer | Technology |
|-------|------------|
| Deployment | Docker Compose |
| Frontend | React 19 + Milkdown 7 + Tailwind 4 |
| Backend | Python (FastAPI) |
| Database | DuckDB |
| AI | Claude API (Haiku 4.5 for extraction, Sonnet 4.5 for queries) |

For detailed technology choices and rationale, see [`docs/tech-stack.md`](./docs/tech-stack.md).

## Project Status

```
✅ Working MVP
   ├── Editor with WYSIWYG toolbar and autosave
   ├── AI-powered data extraction and natural language queries
   ├── Dashboard with charts, heatmaps, and correlations
   ├── Personal kanban with drag-and-drop
   ├── Calendar view and daily note wizard
   ├── Life profile with goals and progress reviews
   └── Containerized with Docker Compose
```

## Getting Started

### Prerequisites

- Docker and Docker Compose
- An Anthropic API key (optional — app works without it, but AI features are disabled)

### Quick Start

```bash
# Clone the repo
git clone https://github.com/dannymawani/unstructured-minds.git
cd unstructured-minds

# Copy environment config
cp docs/.env.example .env

# Add your Anthropic API key (optional)
# Edit .env and set ANTHROPIC_API_KEY=sk-ant-...

# Start development environment
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Frontend: http://localhost:5173
# Backend:  http://localhost:8000
```

### Running Without Docker

```bash
# Backend
cd backend
pip install -e ".[dev]"
python -m uvicorn src.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

### Running Tests

```bash
# Backend tests
cd backend && pytest

# Frontend tests
cd frontend && npm test
```

## Documentation

| Document | Description |
|----------|-------------|
| [`CLAUDE.md`](./CLAUDE.md) | Development guide, skills, agents, workflows |
| [`docs/tech-stack.md`](./docs/tech-stack.md) | Technology choices and rationale |
| [`docs/sales.md`](./docs/sales.md) | Product pitch and feature showcase |
| [`docs/SECURITY.md`](./docs/SECURITY.md) | Security architecture and deployment checklist |
| [`docs/DESIGN_MANUAL.md`](./docs/DESIGN_MANUAL.md) | Visual identity and component styling |
| [`CHANGELOG.md`](./CHANGELOG.md) | Version history |

## Branch Strategy

| Branch | Purpose |
|--------|---------|
| `main` | Stable branch |
| `feature/{name}` | Feature development |
| `fix/{issue}` | Bug fixes |

## Roadmap

- [x] **Phase 0:** Planning & Documentation
- [x] **Phase 1:** Foundation (Backend, Docker, APIs)
- [x] **Phase 2:** Core MVP (Editor, Chat, Extraction)
- [x] **Phase 3:** Polish (Dashboards, Settings)
- [x] **Phase 4:** Kanban, Task System, Calendar
- [x] **Phase 5:** Daily Note Wizard, Life Profile
- [ ] **Phase 6:** Cloud deployment & multi-user

## License

MIT License - see [LICENSE](./LICENSE) for details.

---

Built with Claude as the intelligence layer.
