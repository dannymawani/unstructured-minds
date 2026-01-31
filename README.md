# Unstructured Minds

> Your second brain with a SQL engine underneath.

A standalone desktop application that transforms natural language notes into structured, queryable data. Write naturally in markdown, and let AI extract insights into a personal data warehouse.

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

## Key Features

| Feature | Description |
|---------|-------------|
| **Markdown Editor** | TipTap-powered WYSIWYG editing |
| **Natural Language Logging** | Write freely, data gets extracted |
| **AI-Powered Queries** | Ask questions, get SQL-backed answers |
| **Daily Note Workflow** | One-click daily notes with task rollover |
| **Dashboards** | Visualize your data with charts |
| **Local-First** | All data stays on your machine |
| **Pluggable Storage** | Local filesystem, with cloud options coming |

## Tech Stack

| Layer | Technology |
|-------|------------|
| Desktop | Electron 40.0.0 |
| Frontend | React 19.2.4 + TipTap 3.15.3 |
| Backend | Python 3.14 + FastAPI |
| Database | DuckDB 1.4.4 |
| AI | Claude API (Sonnet 4 / Opus 4) |

## Project Status

```
🟡 Planning Phase
   └── Implementation documents complete
   └── Ready to begin Phase 0: Foundation
```

## Documentation

All planning and implementation docs are in [`/implementation_plan`](./implementation_plan/):

| Document | Description |
|----------|-------------|
| [Vision](./implementation_plan/01-VISION.md) | Product vision and user stories |
| [Architecture](./implementation_plan/02-ARCHITECTURE.md) | System design |
| [Implementation Steps](./implementation_plan/09-IMPLEMENTATION-PLAN-AND-STEPS.md) | Build plan with tests |
| [Decisions](./implementation_plan/07-DECISIONS.md) | Architecture decision records |

## Getting Started

> **Note:** The application is not yet built. This section will be updated as development progresses.

### Prerequisites

- Node.js 22+
- Python 3.14+
- Docker (for development)

### Development Setup

```bash
# Clone the repo
git clone https://github.com/dannymawani/unstructured-minds.git
cd unstructured-minds

# Start development environment
docker-compose up
```

## Branch Strategy

| Branch | Purpose |
|--------|---------|
| `um/main` | Main development branch |
| `um/feature/*` | Feature development |
| `um/release/*` | Release preparation |

## Roadmap

- [x] **Phase 0:** Planning & Documentation
- [ ] **Phase 1:** Foundation (Backend, Docker, APIs)
- [ ] **Phase 2:** Core MVP (Editor, Chat, Extraction)
- [ ] **Phase 3:** Polish (Dashboards, Settings)
- [ ] **Phase 4:** Distribution (Electron packaging)

## License

MIT License - see [LICENSE](./LICENSE) for details.

---

Built with Claude as the intelligence layer.
