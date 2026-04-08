<p align="center">
  <img src="assets/images/um-logo.svg" alt="Unstructured Minds" width="280" />
</p>

<h3 align="center">Your second brain with a SQL engine underneath.</h3>

<p align="center">
  Write naturally in markdown. AI extracts structured data into a personal data warehouse you can query in plain English.
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> &bull;
  <a href="#features">Features</a> &bull;
  <a href="#how-it-works">How It Works</a> &bull;
  <a href="#contributing">Contributing</a>
</p>

---

<!-- TODO: Add screenshot of the editor + dashboard side by side -->
<!-- <p align="center"><img src="assets/images/screenshot.png" width="720" /></p> -->

## How It Works

```
"Had oatmeal for breakfast, then hit the gym — squats 100kg 3x5"
                              |
                        AI extracts data
                              |
            +-----------------+-----------------+
            |                                   |
    food_log: oatmeal              exercise_log: squat
    meal: breakfast                 100kg, 5 reps, 3 sets
            |                                   |
            +-----------------------------------+
                              |
              "How many times did I squat over
               100kg this month?"  -->  6 days
```

## Features

- **Markdown Editor** — Milkdown WYSIWYG with toolbar, templates, and raw toggle
- **AI Extraction** — Write freely, AI extracts food logs, workouts, metrics, and tasks
- **Natural Language Queries** — Ask questions in plain English, get SQL-backed answers
- **Dashboards** — Activity heatmaps, exercise progress, sleep trends, mood correlations, nutrition
- **Daily Note Wizard** — One-click daily notes with structured creation flow
- **Personal Kanban** — Drag-and-drop task board synced with daily note checkboxes
- **Calendar View** — Visual calendar with daily note navigation
- **Note Assistant** — AI chat for editing notes with context
- **Full-Text Search** — Search across all vault notes with snippets and scoring
- **Command Palette** — `Cmd+K` for quick actions
- **Local-First** — All data stays on your machine. Optionally sync to Postgres for multi-user.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 19 + Milkdown 7 + Tailwind 4 |
| Backend | Python 3.12+ / FastAPI |
| Database | DuckDB (local) / Postgres (cloud) |
| AI | Any LLM — Anthropic, OpenAI, Ollama, or [100+ providers via LiteLLM](https://docs.litellm.ai/docs/providers) |
| Auth | None (default) / Basic / [Clerk](https://clerk.com) |
| Deploy | Docker Compose |

## Quick Start

### Prerequisites

- **Docker** and **Docker Compose**
- An LLM API key *(optional — app works without it, AI features are just disabled)*

### 1. Clone and configure

```bash
git clone https://github.com/dannymawani/unstructured_minds.git
cd unstructured_minds
cp .env.example .env
```

### 2. Set your LLM provider (optional)

Edit `.env` and uncomment the provider you want:

```bash
# Anthropic
LLM_PROVIDER=anthropic
LLM_API_KEY=sk-ant-...

# Or OpenAI
# LLM_PROVIDER=openai
# LLM_API_KEY=sk-...

# Or Ollama (free, local)
# LLM_PROVIDER=ollama
```

### 3. Start

```bash
# Development (hot reload)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Or production
docker compose up -d
```

Open **http://localhost:5173** (dev) or **http://localhost:3000** (prod).

### Without Docker

```bash
# Backend
cd backend && pip install -e ".[dev]"
python3 -m uvicorn src.main:app --reload

# Frontend (separate terminal)
cd frontend && npm install && npm run dev
```

### Running Tests

```bash
make test          # all tests
make test-backend  # backend only
make test-frontend # frontend only
```

## Storage Modes

| Mode | Setup | Best For |
|------|-------|----------|
| **Local** (default) | Zero config | Personal use, single machine |
| **Postgres** | `USE_CLOUD=true` + `DATABASE_URL` | Multi-user, server deployment |

With Postgres mode, DuckDB still runs in-memory as a fast analytics cache.

**Bundled Postgres** — no external DB needed:
```bash
docker compose --profile postgres up -d
```

## Authentication

| Mode | Setup | Best For |
|------|-------|----------|
| `none` (default) | Zero config | Local / trusted network |
| `basic` | `AUTH_MODE=basic` + username/password in `.env` | Simple password protection |
| `clerk` | `AUTH_MODE=clerk` + Clerk keys | Multi-user SaaS deployment |

## Documentation

| Document | Description |
|----------|-------------|
| [`.env.example`](./.env.example) | All configuration options, fully commented |
| [`CLAUDE.md`](./CLAUDE.md) | Development guide and project context |
| [`ai_docs/`](./ai_docs/) | Deep technical reference (architecture, schemas, pipelines) |
| [`docs/tech-stack.md`](./docs/tech-stack.md) | Technology choices and rationale |
| [`docs/SECURITY.md`](./docs/SECURITY.md) | Security architecture and checklist |
| [`CONTRIBUTING.md`](./CONTRIBUTING.md) | Contribution guidelines |
| [`CHANGELOG.md`](./CHANGELOG.md) | Version history |

## Contributing

We welcome contributions! See [`CONTRIBUTING.md`](./CONTRIBUTING.md) for guidelines.

```bash
# Fork, clone, branch
git checkout -b feature/your-feature

# Make changes, test
make test

# Submit a PR
```

## Roadmap

- [x] Markdown editor with WYSIWYG + AI extraction
- [x] Natural language queries over personal data
- [x] Dashboards (charts, heatmaps, correlations)
- [x] Personal kanban + calendar + daily wizard
- [x] Cloud deployment + multi-user
- [x] Provider-agnostic AI (LiteLLM)
- [x] Three-mode auth (none / basic / clerk)
- [ ] Multimodal content (images, PDFs)
- [ ] Mobile-friendly PWA
- [ ] Plugin system

## License

MIT — see [LICENSE](./LICENSE) for details.
