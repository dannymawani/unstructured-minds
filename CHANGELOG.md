# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [v1.0.0] - 2026-04-09

Initial open-source release.

### Features
- **Markdown Editor** — Milkdown-based editor with tables, slash commands, and auto-save
- **Daily Note Wizard** — Structured note creation with templates and task rollover
- **AI Extraction** — Natural language notes parsed into structured data (exercises, tasks, nutrition, mood)
- **Natural Language Queries** — Ask questions about your data in plain English
- **Dashboard** — Activity heatmap, exercise tracking with PRs and trends, muscle group heatmap, nutrition and mood charts
- **Exercise Tracking** — Per-set weight/rep logging, auto-labeling with muscle groups, endurance support (pace, distance, heart rate)
- **Task Management** — Kanban board with drag-and-drop, deadlines, and daily note integration
- **Provider-Agnostic AI** — Any LLM via LiteLLM (Anthropic, OpenAI, Ollama, 100+ providers)
- **Two Storage Modes** — Local (DuckDB file) or cloud (Postgres) via `STORAGE_MODE`
- **Three Auth Modes** — `none` (default), `basic`, or `clerk` via `AUTH_MODE`
- **Docker Compose** — Single `docker-compose.yml` for dev and prod (`DEBUG=true` enables hot reload)
- **Interactive Setup** — `make setup` / `./setup.sh` wizard for .env configuration
- **LAN & Tailscale Access** — Serve to other devices on your network or remotely via Tailscale

### Security
- Defense-in-depth for AI-generated SQL (system prompt separation, SQL validation, read-only execution, auto LIMIT)
- Content Security Policy headers via nginx
- Auth guards on all authenticated endpoints
