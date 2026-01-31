# 06 - Implementation Roadmap

## Phased Approach

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Phase 0       │  Phase 1       │  Phase 2       │  Phase 3             │
│  Foundation    │  Core MVP      │  Polish        │  Distribution        │
│  (Week 1)      │  (Week 2-3)    │  (Week 4-5)    │  (Week 6+)           │
├──────────────────────────────────────────────────────────────────────────┤
│  • Project     │  • Editor      │  • Dashboard   │  • App packaging     │
│    setup       │  • Chat        │    views       │  • Documentation     │
│  • FastAPI     │  • Skills      │  • Settings    │  • Distribution      │
│    server      │  • Auto-log    │  • Themes      │  • User feedback     │
│  • DuckDB      │  • Daily note  │  • Polish UX   │                      │
│    schema      │    button      │                │                      │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 0: Foundation (Week 1)

**Goal:** Working backend that can be called from any frontend

### 0.1 Project Structure

```bash
unstructured-minds/
├── backend/                    # Python/FastAPI
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI app
│   │   ├── config.py          # Settings
│   │   ├── claude/
│   │   │   ├── client.py      # Anthropic SDK wrapper
│   │   │   ├── extraction.py  # Data extraction logic
│   │   │   └── skills.py      # Skill execution
│   │   ├── db/
│   │   │   ├── connection.py  # DuckDB connection
│   │   │   ├── schema.py      # Table definitions
│   │   │   └── queries.py     # Common queries
│   │   ├── storage/           # Storage abstraction layer
│   │   │   ├── __init__.py
│   │   │   ├── base.py        # StorageBackend protocol
│   │   │   ├── local.py       # LocalFilesystem (v1.0)
│   │   │   ├── azure.py       # AzureBlobStore (future)
│   │   │   └── s3.py          # S3Backend (future)
│   │   ├── api/
│   │   │   ├── routes.py      # API endpoints
│   │   │   └── models.py      # Pydantic models
│   │   └── watcher/
│   │       └── file_watcher.py
│   ├── tests/
│   ├── Dockerfile             # Production image
│   ├── pyproject.toml
│   └── README.md
├── frontend/                   # React/Vite (Docker)
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── stores/
│   │   └── App.tsx
│   ├── Dockerfile             # Production image (nginx)
│   ├── Dockerfile.dev         # Dev container
│   ├── nginx.conf             # nginx config for SPA
│   ├── package.json
│   └── vite.config.ts
├── skills/                     # Skill definitions
│   ├── daily.md
│   ├── wod.md
│   └── ...
├── k8s/                        # Kubernetes manifests (future)
│   └── README.md
├── docker-compose.yml          # Development environment
├── .env.example                # Environment template
└── README.md
```

### 0.2 Backend Setup

```bash
# Create project
mkdir unstructured-minds && cd unstructured-minds
mkdir -p backend/src/{claude,db,api,watcher}

# Setup Python environment
cd backend
python -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn anthropic duckdb watchdog pydantic python-dotenv
```

### 0.3 Core API Endpoints

```python
# backend/src/api/routes.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Unstructured Minds API")

# ─── Health ───────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok"}

# ─── Vault ────────────────────────────────────────────────────
@app.get("/vault/files")
async def list_files(path: str = "/"):
    """List files in vault directory."""
    pass

@app.get("/vault/file")
async def read_file(path: str):
    """Read a file from vault."""
    pass

@app.post("/vault/file")
async def write_file(path: str, content: str):
    """Write a file to vault."""
    pass

# ─── Extraction ───────────────────────────────────────────────
@app.post("/extract")
async def extract_data(file_path: str):
    """Extract structured data from a file."""
    pass

@app.post("/extract/batch")
async def extract_batch(file_paths: list[str]):
    """Extract from multiple files."""
    pass

# ─── Query ────────────────────────────────────────────────────
@app.post("/query")
async def natural_language_query(question: str):
    """Answer a natural language question."""
    pass

@app.post("/query/sql")
async def sql_query(sql: str):
    """Execute a SQL query directly."""
    pass

# ─── Skills ───────────────────────────────────────────────────
@app.get("/skills")
async def list_skills():
    """List available skills."""
    pass

@app.post("/skills/{skill_name}")
async def execute_skill(skill_name: str, context: dict = None):
    """Execute a skill."""
    pass

# ─── Dashboard ────────────────────────────────────────────────
@app.get("/dashboard/weekly-activity")
async def weekly_activity():
    """Get weekly activity summary."""
    pass

@app.get("/dashboard/metrics")
async def metrics_trends(days: int = 30):
    """Get metrics trends."""
    pass
```

### 0.4 DuckDB Setup

```python
# backend/src/db/schema.py

import duckdb
from pathlib import Path

def init_database(db_path: Path) -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect(str(db_path))

    conn.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            id VARCHAR PRIMARY KEY,
            date DATE NOT NULL,
            type VARCHAR NOT NULL,
            duration_minutes INTEGER,
            notes VARCHAR,
            source_file VARCHAR,
            extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS exercise_log (
            id VARCHAR PRIMARY KEY,
            activity_id VARCHAR NOT NULL,
            date DATE NOT NULL,
            exercise VARCHAR NOT NULL,
            weight_kg DECIMAL(5,1),
            reps INTEGER,
            set_number INTEGER,
            duration_minutes INTEGER,
            distance_km DECIMAL(5,2),
            notes VARCHAR,
            source_file VARCHAR,
            extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_metrics (
            date DATE PRIMARY KEY,
            sleep_hours DECIMAL(3,1),
            sleep_quality INTEGER,
            energy INTEGER,
            mood INTEGER,
            stress INTEGER,
            notes VARCHAR,
            source_file VARCHAR,
            extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS extraction_log (
            id INTEGER PRIMARY KEY,
            file_path VARCHAR NOT NULL,
            file_hash VARCHAR NOT NULL,
            extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            success BOOLEAN,
            error_message VARCHAR
        )
    """)

    return conn
```

### Deliverables - Phase 0

- [ ] Project structure created
- [ ] FastAPI server running on localhost:8000
- [ ] DuckDB schema initialized
- [ ] Basic CRUD endpoints for vault files
- [ ] Claude client wrapper working
- [ ] Can extract data from a single markdown file

---

## Phase 1: Core MVP (Week 2-3)

**Goal:** Usable app with core features

### 1.1 Frontend Setup

```bash
cd frontend
npm create vite@latest . -- --template react-ts
npm install @milkdown/core @milkdown/react @milkdown/preset-commonmark @milkdown/theme-nord
npm install zustand @tanstack/react-query
npm install tailwindcss postcss autoprefixer
npm install lucide-react recharts
npx shadcn-ui@latest init
```

### 1.2 Editor Component

```tsx
// frontend/src/components/Editor/MarkdownEditor.tsx

import { Editor, rootCtx, defaultValueCtx } from '@milkdown/core';
import { commonmark } from '@milkdown/preset-commonmark';
import { nord } from '@milkdown/theme-nord';
import { ReactEditor, useEditor } from '@milkdown/react';
import { listener, listenerCtx } from '@milkdown/plugin-listener';
import { useEffect } from 'react';
import { useVaultStore } from '@/stores/vault';
import { useMutation } from '@tanstack/react-query';
import { saveFile } from '@/api/vault';

export function MarkdownEditor() {
  const { currentFile, content, setContent } = useVaultStore();

  const saveMutation = useMutation({
    mutationFn: saveFile,
    onSuccess: () => {
      // Trigger extraction after save
    }
  });

  const { editor } = useEditor((root) =>
    Editor.make()
      .config((ctx) => {
        ctx.set(rootCtx, root);
        ctx.set(defaultValueCtx, content);
        ctx.get(listenerCtx).markdownUpdated((_, markdown) => {
          setContent(markdown);
        });
      })
      .use(nord)
      .use(commonmark)
      .use(listener)
  );

  // Debounced auto-save
  useEffect(() => {
    const timer = setTimeout(() => {
      if (content && currentFile) {
        saveMutation.mutate({ path: currentFile, content });
      }
    }, 2000);
    return () => clearTimeout(timer);
  }, [content]);

  return (
    <div className="editor-container">
      <ReactEditor editor={editor} />
    </div>
  );
}
```

### 1.3 Chat Interface

```tsx
// frontend/src/components/Chat/ChatInterface.tsx

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { query } from '@/api/claude';

export function ChatInterface() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);

  const queryMutation = useMutation({
    mutationFn: query,
    onSuccess: (response) => {
      setMessages(prev => [...prev, { role: 'assistant', content: response }]);
    }
  });

  const handleSubmit = () => {
    if (!input.trim()) return;

    // Check for skill invocation
    if (input.startsWith('/')) {
      const skillName = input.slice(1).split(' ')[0];
      // Execute skill
    } else {
      // Natural language query
      setMessages(prev => [...prev, { role: 'user', content: input }]);
      queryMutation.mutate(input);
    }
    setInput('');
  };

  return (
    <div className="chat-container">
      <div className="messages">
        {messages.map((m, i) => (
          <div key={i} className={`message ${m.role}`}>
            {m.content}
          </div>
        ))}
      </div>
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
        placeholder="Ask a question or type /skill..."
      />
    </div>
  );
}
```

### 1.4 Daily Note Button

```tsx
// frontend/src/components/Toolbar/DailyNoteButton.tsx

import { useMutation } from '@tanstack/react-query';
import { executeSkill } from '@/api/skills';
import { useVaultStore } from '@/stores/vault';
import { CalendarPlus } from 'lucide-react';

export function DailyNoteButton() {
  const { openFile } = useVaultStore();

  const dailyMutation = useMutation({
    mutationFn: () => executeSkill('daily'),
    onSuccess: (result) => {
      openFile(result.file_path);
    }
  });

  return (
    <button
      onClick={() => dailyMutation.mutate()}
      disabled={dailyMutation.isPending}
      className="daily-note-button"
    >
      <CalendarPlus className="w-5 h-5" />
      {dailyMutation.isPending ? 'Creating...' : 'Daily Note'}
    </button>
  );
}
```

### Deliverables - Phase 1

- [ ] React app with Milkdown editor
- [ ] File browser sidebar
- [ ] Chat interface for queries
- [ ] Command palette (Cmd+K)
- [ ] Daily note button working
- [ ] Auto-extraction on file save
- [ ] Basic skill execution (/daily, /wod)
- [ ] File watcher for external changes

---

## Phase 2: Polish (Week 4-5)

**Goal:** Refined UX, dashboards, settings

### 2.1 Dashboard Views

```tsx
// frontend/src/components/Dashboard/WeeklyActivity.tsx

import { useQuery } from '@tanstack/react-query';
import { BarChart, Bar, XAxis, YAxis, Tooltip } from 'recharts';
import { getWeeklyActivity } from '@/api/dashboard';

export function WeeklyActivity() {
  const { data, isLoading } = useQuery({
    queryKey: ['weekly-activity'],
    queryFn: getWeeklyActivity
  });

  if (isLoading) return <div>Loading...</div>;

  return (
    <div className="dashboard-panel">
      <h3>Weekly Activity</h3>
      <BarChart width={400} height={200} data={data}>
        <XAxis dataKey="day" />
        <YAxis />
        <Tooltip />
        <Bar dataKey="duration" fill="#8884d8" name="Minutes" />
      </BarChart>
    </div>
  );
}
```

### 2.2 Settings Panel

```tsx
// Settings configuration
interface Settings {
  vault: {
    path: string;
    autoExtract: boolean;
    extractDebounceMs: number;
  };
  claude: {
    apiKey: string;  // Stored in keychain
    model: 'sonnet' | 'opus';
    maxTokens: number;
  };
  ui: {
    theme: 'light' | 'dark' | 'system';
    fontSize: number;
    showLineNumbers: boolean;
  };
}
```

### Deliverables - Phase 2

- [ ] Weekly activity dashboard
- [ ] Exercise progress charts
- [ ] Metrics trends visualization
- [ ] Settings panel with configuration
- [ ] Dark mode support
- [ ] Keyboard shortcuts (Cmd+K, Cmd+S, etc.)
- [ ] Error handling and notifications
- [ ] Loading states and skeletons

---

## Phase 3: Production Deployment (Week 6+)

**Goal:** Containerized web app ready for deployment

### 3.1 Production Docker Configuration

```dockerfile
# frontend/Dockerfile
FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

```nginx
# frontend/nginx.conf
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3.2 Production Docker Compose

```yaml
# docker-compose.prod.yml
services:
  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: unless-stopped

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ${VAULT_PATH:-./vault}:/app/vault
      - ${DATA_PATH:-./data}:/app/data
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Deliverables - Phase 3

- [ ] Production Docker images building
- [ ] docker-compose.prod.yml working
- [ ] Health checks configured
- [ ] Data persists across restarts
- [ ] User documentation
- [ ] Deployment guide

---

## Docker Compose Setup

### docker-compose.yml

```yaml
version: "3.9"

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    volumes:
      # Vault directory - your markdown files
      - ${VAULT_PATH:-~/vault}:/app/vault:rw
      # Data directory - DuckDB, cache, config
      - ${DATA_PATH:-~/.unstructured}:/app/data:rw
      # Source code for hot reload
      - ./backend/src:/app/src:ro
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - VAULT_PATH=/app/vault
      - DATA_PATH=/app/data
      - PYTHONUNBUFFERED=1
    # Match host user to avoid permission issues
    user: "${UID:-1000}:${GID:-1000}"
    command: uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    ports:
      - "5173:5173"
    volumes:
      - ./frontend/src:/app/src:ro
      - ./frontend/public:/app/public:ro
    environment:
      - VITE_API_URL=http://localhost:8000
    depends_on:
      - backend
    command: npm run dev -- --host 0.0.0.0

# Optional: named volumes for persistence
volumes:
  duckdb_data:
```

### backend/Dockerfile

```dockerfile
FROM python:3.14-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# Copy source
COPY src/ ./src/

# Create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### .env.example

```bash
# Copy to .env and fill in values
ANTHROPIC_API_KEY=sk-ant-...

# Paths (defaults work for most setups)
VAULT_PATH=~/vault
DATA_PATH=~/.unstructured

# User mapping for volume permissions (run: id -u && id -g)
UID=1000
GID=1000
```

### Volume Permissions

To ensure the container can write to mounted volumes:

```bash
# Option 1: Match container user to host user (recommended)
export UID=$(id -u)
export GID=$(id -g)
docker-compose up

# Option 2: Fix permissions on host directories
chmod -R 775 ~/vault ~/.unstructured

# Option 3: Run as root (not recommended for production)
# Remove 'user:' line from docker-compose.yml
```

---

## Development Commands

```bash
# Backend development (native)
cd backend
source .venv/bin/activate
uvicorn src.main:app --reload --port 8000

# Frontend development (native)
cd frontend
npm run dev

# Run both with Docker Compose (recommended)
docker-compose up

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f backend

# Rebuild after dependency changes
docker-compose build --no-cache

# Stop and remove containers
docker-compose down

# Build production images
docker-compose -f docker-compose.prod.yml build
```

---

## Future: Kubernetes (Minikube)

When ready for production testing:

```bash
# Generate k8s manifests from compose
kompose convert -f docker-compose.yml

# Or use Helm chart (to be created)
helm install unstructured-minds ./helm/

# Minikube with local volume
minikube start
minikube mount ~/vault:/vault
```

K8s manifests will be added to `k8s/` directory when approaching production.

---

## Testing Strategy

| Layer | Tool | What to Test |
|-------|------|--------------|
| Backend | pytest | API endpoints, extraction logic, DuckDB queries |
| Frontend | Vitest | Components, hooks, stores |
| E2E | Playwright | Full user flows |
| Integration | pytest | Claude API mocking |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Claude API costs | Caching, batching, model selection (Haiku for extraction) |
| Editor complexity | Start with Milkdown defaults, customize later |
| DuckDB size | Periodic cleanup, archiving old data |
| Docker complexity | Use docker-compose for simplicity |
| Volume permissions | Document user mapping, provide helper scripts |

---

*Next: [07-DECISIONS.md](./07-DECISIONS.md)*
