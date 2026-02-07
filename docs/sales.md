# Unstructured Minds: Sales Pitch

## The Hook

**Your second brain with a SQL engine underneath.**

Turn scattered notes into structured intelligence. Write naturally in markdown, let Claude extract the data, and query your entire life with plain English.

---

## The Problem

Your digital life is fragmented. You jot down workouts, meals, moods, and thoughts in natural language. Each entry feels complete in the moment, but the insights are trapped inside thousands of unstructured notes. Questions like "What was my average sleep duration last month?" or "Which workouts correlated with my best energy levels?" require hours of manual review.

Popular note-taking apps are built for capture, not insight. They excel at letting you write freely but fail at helping you understand patterns in what you've written. Spreadsheets demand rigid structure upfront. Your notes deserve both—the flexibility to write naturally and the power to query meaningfully.

---

## The Solution

Unstructured Minds bridges that gap. It's a containerized web app that transforms natural language into queryable data using Claude AI and DuckDB.

The workflow is simple:

1. **Write Naturally** — Use a Milkdown-powered markdown editor with templates, WYSIWYG toolbar, and real-time autosave. No structure required.
2. **Extract Automatically** — Claude AI reads your notes and extracts structured data into a personal data warehouse. Meals become nutritional logs. Workouts become exercise records. Moods become correlatable signals.
3. **Query Your Life** — Ask questions in plain English: "How many times did I squat over 100kg?" or "What's my average sleep when I exercise?" DuckDB powers instant, accurate answers.

The entire app runs locally in Docker. Your data never leaves your machine. You control the extraction rules through configuration files. You own everything.

---

## What You Get

### The Editor
A beautiful markdown editor built with React 19 and Milkdown 7. WYSIWYG toolbar for common formatting. Templates for consistency. Raw markdown toggle for power users. Real-time autosave so you never lose work. Every note organized in a daily structure.

### AI-Powered Extraction
Claude analyzes your notes and automatically extracts:
- Exercise logs (exercises, sets, reps, weights, duration)
- Food logs (meals, ingredients, calories, macros)
- Sleep data (bedtime, wake time, quality, disturbances)
- Mood and energy levels
- Custom data types you define

Extraction runs asynchronously. You write; the AI catches up in the background. Mistakes are easy to fix through a simple CSV interface.

### Natural Language Queries
Ask your data anything in plain English. The backend translates questions to SQL using Claude Sonnet and DuckDB returns precise answers. Examples:
- "How many times did I squat over 100kg this month?"
- "What's my average sleep when I exercise 5+ times per week?"
- "Which meals have I logged most often?"
- "Show me mood correlations with caffeine intake"

### Dashboards
Pre-built visualizations reveal patterns:
- Activity heatmaps (when do you exercise?)
- Exercise progress charts (strength trends, volume over time)
- Sleep trends (duration, quality, consistency)
- Mood correlations (what affects your mental state?)
- Custom metrics you care about

### Personal Kanban
A drag-and-drop task board synced with your daily notes. Check off tasks in markdown checkboxes; they appear on the board. Move them on the board; they sync back to your notes. Two-way synchronization means your task system is wherever you're most productive.

### Calendar View
Visual calendar with daily note navigation. Click any date to jump to that note. Color coding shows activity types. See your entire life at a glance.

### Daily Note Wizard
Create daily notes in seconds. The wizard steps you through structured prompts for the day ahead—goals, predictions, intentions. Templates ensure consistency. One-click creation from the dashboard.

### Life Profile
A single page showing:
- Personal goals and progress toward them
- Athletic training data and periodization
- Progress reviews (what's working? what's not?)
- Historical achievements and trends

### Note Assistant
An AI chat window for editing your current note. Ask it to expand a section, rewrite for clarity, suggest structure, or analyze tone. Upload images to your notes and let Claude describe them or extract data from them.

### Full-Text Search
Search across every note simultaneously. Results show matching snippets and relevance scores. Find that workout from three months ago instantly.

### Command Palette
Press Cmd+K for quick navigation. Search notes, run queries, create tasks, access settings. Keyboard-first experience for power users.

### Local-First by Design
All data lives in DuckDB on your machine. No cloud sync delays. No privacy concerns. Full control over your data. Optional Anthropic API key for AI features; everything else works offline.

---

## How It Works

### Step 1: Write

Open your daily note. Write naturally about your day using plain language:

```
Morning: Had oatmeal with berries and coffee. Felt energized.

Gym: Did 5x5 squats at 100kg, then 3x8 bench at 80kg. Good session.

Evening: Went for a 3-mile run at easy pace. 35 minutes.
Total sleep last night: 7.5 hours. Woke up once.
Mood: 8/10. Productive day.
```

### Step 2: Extract

Claude reads your note in the background. The extraction engine identifies:
- Nutrition: oatmeal, berries, coffee
- Exercise: squats (5 sets, 5 reps, 100kg), bench press (3 sets, 8 reps, 80kg), running (3 miles, 35 minutes)
- Sleep: 7.5 hours, 1 disruption
- Mood: 8/10

Structured records are created in DuckDB automatically. A simple CSV view lets you correct any mistakes.

### Step 3: Query

Ask your data anything:

```
"How many times did I squat over 100kg this month?"
→ 6 times

"What's my average sleep when I exercise?"
→ 7.2 hours

"Show me correlation between mood and daily exercise volume"
→ [Visualization of positive correlation]
```

Claude translates your question to SQL. DuckDB returns results instantly. Visualizations are generated automatically.

---

## Built on Modern Technology

| Layer | Technology | Why |
|-------|-----------|-----|
| **Frontend** | React 19 + Milkdown 7 + Tailwind 4 | Modern, reactive, beautiful UI. Milkdown gives you WYSIWYG without sacrificing markdown power. |
| **Backend** | Python 3.14 + FastAPI | Fast, async-ready. Native integration with Claude API. Perfect for AI-driven extraction. |
| **Database** | DuckDB 1.4 | Lightweight SQL engine for personal data warehouses. No server overhead. Runs on your machine. |
| **AI** | Claude API | Haiku 4.5 for extraction (fast, cheap). Sonnet 4.5 for queries (accurate, nuanced). |
| **Deployment** | Docker Compose | Single command startup. Works on macOS, Linux, Windows. Consistent environment everywhere. |

Every layer is chosen for simplicity, performance, and reliability. No unnecessary complexity. No vendor lock-in.

---

## The Credibility Factor

This is a working MVP, not vaporware. Every feature listed above is functional today:

- Editor with autosave? Live.
- AI extraction? Thousands of notes processed.
- Natural language queries? Tested and accurate.
- Dashboards with real data? Working.
- Personal kanban with sync? Implemented.
- Full-text search? Indexed and fast.
- Calendar navigation? Point and click.
- Life profile with goals? Live.

The codebase is clean, well-tested, and open for inspection. Development follows a rigorous workflow: plan, approve, implement, test, review, deploy. No shortcuts.

---

## Who Is This For?

**Athletes** — Track training volume, intensity, and recovery. Correlate workouts with performance and mood.

**Quantified Self Enthusiasts** — Capture everything: sleep, nutrition, exercise, mood, productivity. Find your own patterns.

**Knowledge Workers** — Log projects, learnings, and reflections. Query your professional growth.

**Researchers & Academics** — Collect observational data in natural language. Extract and analyze at scale.

**Health-Conscious Individuals** — Track fitness, nutrition, and wellness without rigid data entry.

**Anyone with a journal** — Keep your existing writing practice and unlock insights from it.

---

## Getting Started

### Option 1: Docker (Recommended)

```bash
git clone https://github.com/dannymawani/unstructured-minds.git
cd unstructured-minds

cp docs/.env.example .env
# Add your Anthropic API key (optional)

docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Open http://localhost:5173. Start writing.

### Option 2: Development Setup

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

Open http://localhost:5173.

### Option 3: Cloud Deployment

See `docs/SECURITY.md` for multi-user deployment guidance.

---

## Why Not Spreadsheets?

Spreadsheets demand structure upfront. You have to know what you're measuring before you start. Unstructured Minds flips this: write naturally, add structure later through extraction rules.

## Why Not Other Note Apps?

Popular note apps (Obsidian, Logseq, Notion) excel at organization but offer minimal querying. Unstructured Minds adds a SQL engine underneath your notes. You get the writing experience you love plus the data insights they can't provide.

## Why Not a Personal Data Dashboard?

Existing dashboards (Apple Health, Fitbit, Strava) integrate with wearables and apps, but they don't capture subjective data—mood, context, learnings. Unstructured Minds lets you log everything from notes and extract any data type you define.

---

## Join the Development

Unstructured Minds is open source (MIT License). Contributions welcome. The development guide in `CLAUDE.md` explains the workflow. The tech stack is straightforward. No monolithic frameworks. Just Python, React, and DuckDB—tools most developers already know.

Roadmap highlights:
- Phase 6: Cloud deployment and multi-user support
- Integration with common APIs (Apple Health, Strava, Fitbit)
- Mobile app or mobile web experience
- Community-contributed extraction templates

---

## The Ask

**Try it. Run it locally. Write a week of daily notes. Run a query. Tell us what you think.**

The full source code is open on GitHub. The Docker setup takes five minutes. Your data stays on your machine. There's no sales funnel, no upsell, no catch. This is a tool built by someone who uses it every day.

Welcome to your second brain with a SQL engine underneath.

---

**Getting started?** Clone the repo, run Docker Compose, open http://localhost:5173, and write your first note.

**Have feedback?** Open an issue on GitHub or reach out.

**Want to contribute?** See `CONTRIBUTING.md` for the development workflow.
