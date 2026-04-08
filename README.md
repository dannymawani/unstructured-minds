<p align="center">
  <img src="assets/images/um-logo.svg" alt="Unstructured Minds" width="280" />
</p>

<h3 align="center">Your second brain with a SQL engine underneath.</h3>

<p align="center">
  Write naturally in markdown. AI extracts structured data into a personal data warehouse you can query in plain English.
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/github/license/dannymawani/unstructured-minds" alt="License" /></a>
  <a href="https://github.com/dannymawani/unstructured-minds/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/dannymawani/unstructured-minds/ci.yml?branch=main&label=CI" alt="CI Status" /></a>
  <a href="https://github.com/dannymawani/unstructured-minds/stargazers"><img src="https://img.shields.io/github/stars/dannymawani/unstructured-minds?style=social" alt="GitHub Stars" /></a>
  <img src="https://img.shields.io/badge/docker-compose-2496ED?logo=docker&logoColor=white" alt="Docker Compose" />
  <img src="https://img.shields.io/badge/python-3.12+-3776AB?logo=python&logoColor=white" alt="Python 3.12+" />
  <img src="https://img.shields.io/badge/react-19-61DAFB?logo=react&logoColor=black" alt="React 19" />
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> &bull;
  <a href="#features">Features</a> &bull;
  <a href="#how-it-works">How It Works</a> &bull;
  <a href="#contributing">Contributing</a>
</p>

---

<p align="center">
  <img src="assets/screenshots/dashboard.png" alt="Dashboard — activity heatmap, nutrition, insights" width="720" />
</p>

## Why Unstructured Minds?

Most note apps let you write but not **query**. Most data tools need structure upfront. Unstructured Minds bridges the gap — write freely in markdown, and AI turns your notes into a personal data warehouse. Track workouts, food, sleep, mood, or anything else, then ask questions like *"How many times did I squat over 100kg this month?"* and get real answers backed by SQL.

Everything runs on your machine. No cloud required. No vendor lock-in.

## How It Works

```mermaid
graph TD
    A["📝 Write a Note\n'Had oatmeal for breakfast,\nthen hit the gym — squats 100kg 3x5'"]

    A --> B["🤖 AI Extraction\nLiteLLM · Anthropic · OpenAI · Ollama"]

    B --> C["🍽️ food_log\noatmeal · breakfast"]
    B --> D["💪 exercise_log\nsquat · 100kg · 5 reps · 3 sets"]

    C --> E[("🗄️ Personal Data Warehouse\nDuckDB · Postgres")]
    D --> E

    E --> F["❓ Ask in Plain English\n'How many times did I squat\nover 100kg this month?'"]

    F --> G["✅ SQL-Backed Answer\n6 days"]

    style A fill:#dbeafe,stroke:#3b82f6,color:#1e3a5f
    style B fill:#fef3c7,stroke:#f59e0b,color:#78350f
    style C fill:#dcfce7,stroke:#22c55e,color:#14532d
    style D fill:#dcfce7,stroke:#22c55e,color:#14532d
    style E fill:#ede9fe,stroke:#8b5cf6,color:#2e1065
    style F fill:#fce7f3,stroke:#ec4899,color:#500724
    style G fill:#dcfce7,stroke:#16a34a,color:#14532d
```

> **Works without an LLM** — the editor, calendar, kanban, and search all work offline. AI features (extraction and natural language queries) require an API key or a local Ollama instance.

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
git clone https://github.com/dannymawani/unstructured-minds.git
cd unstructured-minds

# Interactive setup — walks you through LLM, storage, and auth
make setup

# Or do it manually
cp .env.example .env
```

### 2. Start

```bash
docker compose up --build
```

Open **http://localhost:3000**.

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
| **Postgres** | `STORAGE_MODE=postgres` + `DATABASE_URL` | Multi-user, server deployment |

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

## Remote Access (Tailscale)

Access from your phone, tablet, or anywhere — encrypted, no port forwarding needed.

1. Install [Tailscale](https://tailscale.com/) on your server + devices
2. Add your Tailscale hostname to `CORS_ORIGINS` in `.env`
3. Open `http://your-hostname:3000` from any device on your tailnet

See [`docs/LAN_ACCESS.md`](./docs/LAN_ACCESS.md) for full setup including LAN-only access.

## Documentation

| Document | Description |
|----------|-------------|
| [`.env.example`](./.env.example) | All configuration options, fully commented |
| [`CLAUDE.md`](./CLAUDE.md) | Development guide and project context |
| [`ai_docs/`](./ai_docs/) | Deep technical reference (architecture, schemas, pipelines) |
| [`docs/tech-stack.md`](./docs/tech-stack.md) | Technology choices and rationale |
| [`docs/SECURITY.md`](./docs/SECURITY.md) | Security architecture and checklist |
| [`CONTRIBUTING.md`](./CONTRIBUTING.md) | Contribution guidelines |
| [`SUPPORT.md`](./SUPPORT.md) | Getting help and common issues |
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

## License

MIT — see [LICENSE](./LICENSE) for details.
