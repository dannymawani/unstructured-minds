# 09 - Implementation Plan & Steps

## Git Branch Strategy

### Branch Naming Convention

| Branch | Purpose |
|--------|---------|
| `um/main` | Main development branch (protected) |
| `um/feature/<name>` | Feature development |
| `um/bugfix/<name>` | Bug fixes |
| `um/hotfix/<name>` | Critical production fixes |
| `um/release/<version>` | Release preparation |

### Branch Flow

```
um/main (protected)
    │
    ├── um/feature/phase0-project-setup
    │       │
    │       └── PR → Code Review → Merge to um/main
    │
    ├── um/feature/phase0-fastapi-backend
    │       │
    │       └── PR → Code Review → Merge to um/main
    │
    └── um/release/v0.1.0
            │
            └── Tag → Deploy
```

### Branch Rules

1. **Never commit directly to `um/main`**
2. All changes via Pull Request
3. Require at least 1 approval (self-review for solo dev)
4. All tests must pass before merge
5. Squash merge for clean history

---

## Development Workflow: Design → Test → Build → Review

Each feature follows this cycle:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FEATURE WORKFLOW                                │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  1. DESIGN                                                                   │
│                                                                              │
│  • Create issue/ticket describing feature                                   │
│  • Write acceptance criteria                                                │
│  • Design API contracts (if applicable)                                     │
│  • Update architecture docs if needed                                       │
│  • Create branch: um/feature/<name>                                         │
│                                                                              │
│  Output: Design doc or issue with clear requirements                        │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  2. TEST (Write tests first - TDD)                                          │
│                                                                              │
│  • Write failing unit tests for new functionality                           │
│  • Write integration tests for API endpoints                                │
│  • Define test fixtures and mocks                                           │
│  • Run tests: all should fail (red phase)                                   │
│                                                                              │
│  Output: Test files that define expected behavior                           │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  3. BUILD                                                                    │
│                                                                              │
│  • Implement feature to make tests pass                                     │
│  • Follow coding standards and patterns                                     │
│  • Document code where needed                                               │
│  • Run tests: all should pass (green phase)                                 │
│  • Refactor if needed (refactor phase)                                      │
│                                                                              │
│  Output: Working implementation with passing tests                          │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  4. REVIEW                                                                   │
│                                                                              │
│  • Self-review: check for obvious issues                                    │
│  • Create Pull Request with description                                     │
│  • Run CI pipeline (tests, linting, type checks)                           │
│  • Code review (peer or self with checklist)                               │
│  • Address feedback, update PR                                              │
│  • Merge to um/main when approved                                           │
│                                                                              │
│  Output: Merged, tested feature in um/main                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 0: Foundation

**Goal:** Working backend infrastructure, Docker setup, core APIs

**Branch:** `um/feature/phase0-foundation`

### Step 0.1: Project Initialization

| Task | Test | Acceptance Criteria |
|------|------|---------------------|
| Create repository | N/A | Repo exists at GitHub |
| Create `um/main` branch | N/A | Branch protected |
| Set up `.gitignore` | N/A | Ignores venv, node_modules, .env, __pycache__ |
| Add LICENSE | N/A | MIT license file |
| Create README.md | N/A | Basic project description |

**Branch:** `um/feature/phase0-init`

```bash
# Commands
git init unstructured-minds
cd unstructured-minds
git checkout -b um/main
git checkout -b um/feature/phase0-init
```

---

### Step 0.2: Backend Project Structure

| Task | Test | Acceptance Criteria |
|------|------|---------------------|
| Create backend folder structure | `test_project_structure.py` | All dirs exist |
| Set up pyproject.toml | `pip install -e .` succeeds | Package installs |
| Configure pytest | `pytest --collect-only` | Tests discovered |
| Add .env.example | N/A | Template exists |

**Branch:** `um/feature/phase0-backend-structure`

**Tests:**
```python
# backend/tests/test_project_structure.py
def test_src_directory_exists():
    assert Path("backend/src").exists()

def test_required_modules_exist():
    modules = ["claude", "db", "api", "storage", "watcher"]
    for mod in modules:
        assert Path(f"backend/src/{mod}").exists()
```

---

### Step 0.3: Docker Compose Setup

| Task | Test | Acceptance Criteria |
|------|------|---------------------|
| Create Dockerfile | `docker build .` succeeds | Image builds |
| Create docker-compose.yml | `docker-compose config` valid | Config validates |
| Test volume mounts | Write test file | File accessible on host |
| Add .env.example | N/A | All vars documented |

**Branch:** `um/feature/phase0-docker`

**Tests:**
```bash
# Manual test script: scripts/test_docker.sh
docker-compose up -d
curl http://localhost:8000/health
docker-compose down
```

---

### Step 0.4: FastAPI Backend

| Task | Test | Acceptance Criteria |
|------|------|---------------------|
| Create FastAPI app | `test_health_endpoint` | GET /health returns 200 |
| Add CORS middleware | N/A | Frontend can connect |
| Create config module | `test_config_loads` | Config from env vars |
| Add logging | N/A | Structured logs output |

**Branch:** `um/feature/phase0-fastapi`

**Tests:**
```python
# backend/tests/test_api.py
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_config_loads():
    from src.config import settings
    assert settings.vault_path is not None
```

---

### Step 0.5: Storage Abstraction Layer

| Task | Test | Acceptance Criteria |
|------|------|---------------------|
| Define StorageBackend protocol | `test_protocol_defined` | Interface exists |
| Implement LocalFilesystem | `test_local_read_write` | CRUD operations work |
| Add factory function | `test_get_storage_backend` | Returns correct backend |

**Branch:** `um/feature/phase0-storage`

**Tests:**
```python
# backend/tests/test_storage.py
import pytest
from src.storage.local import LocalFilesystem

@pytest.fixture
def storage(tmp_path):
    return LocalFilesystem(base_path=tmp_path)

async def test_write_and_read(storage):
    await storage.write("test.md", b"# Hello")
    content = await storage.read("test.md")
    assert content == b"# Hello"

async def test_list_files(storage):
    await storage.write("a.md", b"a")
    await storage.write("b.md", b"b")
    files = await storage.list("")
    assert set(files) == {"a.md", "b.md"}

async def test_delete(storage):
    await storage.write("delete-me.md", b"bye")
    await storage.delete("delete-me.md")
    assert not await storage.exists("delete-me.md")
```

---

### Step 0.6: DuckDB Setup

| Task | Test | Acceptance Criteria |
|------|------|---------------------|
| Create schema.py | `test_schema_creation` | Tables created |
| Add connection manager | `test_connection` | Can connect/query |
| Create migration system | `test_migrations` | Versions tracked |

**Branch:** `um/feature/phase0-duckdb`

**Tests:**
```python
# backend/tests/test_db.py
import duckdb
from src.db.schema import init_database

def test_schema_creation(tmp_path):
    db_path = tmp_path / "test.duckdb"
    conn = init_database(db_path)

    # Verify tables exist
    tables = conn.execute(
        "SELECT table_name FROM information_schema.tables"
    ).fetchall()
    table_names = [t[0] for t in tables]

    assert "exercise_log" in table_names
    assert "daily_metrics" in table_names
    assert "extraction_log" in table_names

def test_insert_and_query(tmp_path):
    db_path = tmp_path / "test.duckdb"
    conn = init_database(db_path)

    conn.execute("""
        INSERT INTO exercise_log (id, activity_id, date, exercise)
        VALUES ('test1', 'act1', '2026-01-31', 'squat')
    """)

    result = conn.execute("SELECT exercise FROM exercise_log").fetchone()
    assert result[0] == "squat"
```

---

### Step 0.7: Claude Client

| Task | Test | Acceptance Criteria |
|------|------|---------------------|
| Create ClaudeClient class | `test_client_init` | Client initializes |
| Add extraction method | `test_extraction_mock` | Returns structured JSON |
| Add query method | `test_query_mock` | Returns response |
| Handle errors/retries | `test_retry_logic` | Retries on failure |

**Branch:** `um/feature/phase0-claude`

**Tests:**
```python
# backend/tests/test_claude.py
import pytest
from unittest.mock import AsyncMock, patch
from src.claude.client import ClaudeClient

@pytest.fixture
def mock_anthropic():
    with patch("src.claude.client.Anthropic") as mock:
        yield mock

def test_client_init(mock_anthropic):
    client = ClaudeClient()
    assert client.model == "claude-sonnet-4-20250514"

async def test_extraction_returns_json(mock_anthropic):
    mock_response = AsyncMock()
    mock_response.content = [AsyncMock(text='{"exercise_log": []}')]
    mock_anthropic.return_value.messages.create = AsyncMock(return_value=mock_response)

    client = ClaudeClient()
    result = await client.extract("# Test content", {})

    assert "exercise_log" in result
```

---

### Phase 0 Completion Checklist

- [ ] `um/feature/phase0-init` merged
- [ ] `um/feature/phase0-backend-structure` merged
- [ ] `um/feature/phase0-docker` merged
- [ ] `um/feature/phase0-fastapi` merged
- [ ] `um/feature/phase0-storage` merged
- [ ] `um/feature/phase0-duckdb` merged
- [ ] `um/feature/phase0-claude` merged
- [ ] All tests passing
- [ ] Docker Compose runs successfully
- [ ] API accessible at localhost:8000

**Release:** Tag `v0.1.0-alpha` on `um/main`

---

## Phase 1: Core MVP

**Goal:** Usable app with editor, chat, daily note, extraction

### Step 1.1: Frontend Project Setup

| Task | Test | Acceptance Criteria |
|------|------|---------------------|
| Create Vite + React project | `npm run build` succeeds | Build works |
| Add TypeScript config | Type check passes | No TS errors |
| Configure Tailwind | Styles apply | CSS works |
| Add shadcn/ui | Components render | Button renders |

**Branch:** `um/feature/phase1-frontend-setup`

**Tests:**
```typescript
// frontend/src/__tests__/setup.test.tsx
import { render } from '@testing-library/react';
import { Button } from '@/components/ui/button';

test('shadcn button renders', () => {
  const { getByText } = render(<Button>Click me</Button>);
  expect(getByText('Click me')).toBeInTheDocument();
});
```

---

### Step 1.2: TipTap Editor

| Task | Test | Acceptance Criteria |
|------|------|---------------------|
| Install TipTap packages | N/A | Packages installed |
| Create MarkdownEditor component | `test_editor_renders` | Editor displays |
| Add markdown export | `test_markdown_export` | Returns valid MD |
| Add auto-save | `test_auto_save` | Debounced save works |

**Branch:** `um/feature/phase1-editor`

**Tests:**
```typescript
// frontend/src/components/Editor/__tests__/MarkdownEditor.test.tsx
import { render, fireEvent, waitFor } from '@testing-library/react';
import { MarkdownEditor } from '../MarkdownEditor';

test('editor renders with initial content', () => {
  const { container } = render(
    <MarkdownEditor content="# Hello" onChange={() => {}} />
  );
  expect(container.querySelector('.ProseMirror')).toBeInTheDocument();
});

test('editor exports markdown', async () => {
  let exported = '';
  render(
    <MarkdownEditor
      content="# Test"
      onChange={(md) => { exported = md; }}
    />
  );
  await waitFor(() => {
    expect(exported).toContain('# Test');
  });
});
```

---

### Step 1.3: Vault API Endpoints

| Task | Test | Acceptance Criteria |
|------|------|---------------------|
| GET /vault/files | `test_list_files` | Returns file tree |
| GET /vault/file | `test_read_file` | Returns content |
| POST /vault/file | `test_write_file` | Saves content |
| DELETE /vault/file | `test_delete_file` | Removes file |

**Branch:** `um/feature/phase1-vault-api`

**Tests:**
```python
# backend/tests/test_vault_api.py
def test_list_files(client, vault_with_files):
    response = client.get("/vault/files")
    assert response.status_code == 200
    assert "Daily-Notes" in response.json()["files"]

def test_read_file(client, vault_with_files):
    response = client.get("/vault/file?path=Daily-Notes/2026-01/2026-01-31.md")
    assert response.status_code == 200
    assert "# Daily Note" in response.json()["content"]

def test_write_file(client, vault_with_files):
    response = client.post("/vault/file", json={
        "path": "test.md",
        "content": "# Test"
    })
    assert response.status_code == 200
```

---

### Step 1.4: File Browser Component

| Task | Test | Acceptance Criteria |
|------|------|---------------------|
| Create FileTree component | `test_tree_renders` | Tree displays |
| Add expand/collapse | `test_expand_folder` | Folders toggle |
| Add file selection | `test_select_file` | Callback fires |
| Connect to API | `test_loads_files` | Fetches from backend |

**Branch:** `um/feature/phase1-file-browser`

---

### Step 1.5: Chat Interface

| Task | Test | Acceptance Criteria |
|------|------|---------------------|
| Create ChatInterface component | `test_chat_renders` | Chat displays |
| Add message history | `test_messages_display` | Shows history |
| Connect to query API | `test_sends_query` | Calls backend |
| Parse /skill commands | `test_skill_detection` | Detects /daily |

**Branch:** `um/feature/phase1-chat`

---

### Step 1.6: Daily Note Skill

| Task | Test | Acceptance Criteria |
|------|------|---------------------|
| POST /skills/daily endpoint | `test_daily_skill` | Creates note |
| Task rollover logic | `test_task_rollover` | Incomplete tasks copy |
| Template generation | `test_template` | Proper structure |
| Daily Note button | `test_button_creates_note` | One-click works |

**Branch:** `um/feature/phase1-daily-skill`

**Tests:**
```python
# backend/tests/test_skills.py
async def test_daily_skill_creates_note(client, mock_claude):
    response = await client.post("/skills/daily")
    assert response.status_code == 200
    assert "file_path" in response.json()

    # Verify file was created
    file_response = await client.get(
        f"/vault/file?path={response.json()['file_path']}"
    )
    assert file_response.status_code == 200
```

---

### Step 1.7: Data Extraction

| Task | Test | Acceptance Criteria |
|------|------|---------------------|
| POST /extract endpoint | `test_extract_endpoint` | Extracts data |
| File watcher integration | `test_watcher_triggers` | Auto-extracts on save |
| Upsert to DuckDB | `test_data_persists` | Data in database |
| extraction_log tracking | `test_skip_unchanged` | Skips if hash matches |

**Branch:** `um/feature/phase1-extraction`

---

### Phase 1 Completion Checklist

- [ ] All Phase 1 branches merged
- [ ] Editor loads and saves files
- [ ] File browser navigates vault
- [ ] Chat interface sends queries
- [ ] /daily skill creates notes
- [ ] Extraction populates DuckDB
- [ ] All tests passing

**Release:** Tag `v0.2.0-beta` on `um/main`

---

## Phase 2: Polish

**Goal:** Dashboards, settings, themes, UX refinement

### Step 2.1: Dashboard API

| Task | Test | Acceptance Criteria |
|------|------|---------------------|
| GET /dashboard/weekly-activity | `test_weekly_activity` | Returns chart data |
| GET /dashboard/metrics-trends | `test_metrics_trends` | Returns time series |
| GET /dashboard/exercise-progress | `test_exercise_progress` | Returns progress |

**Branch:** `um/feature/phase2-dashboard-api`

---

### Step 2.2: Dashboard UI

| Task | Test | Acceptance Criteria |
|------|------|---------------------|
| WeeklyActivity component | `test_chart_renders` | Chart displays |
| MetricsTrends component | `test_trends_render` | Line chart works |
| Dashboard layout | `test_layout` | Responsive grid |

**Branch:** `um/feature/phase2-dashboard-ui`

---

### Step 2.3: Settings Panel

| Task | Test | Acceptance Criteria |
|------|------|---------------------|
| Settings component | `test_settings_render` | Form displays |
| Vault path config | `test_vault_path` | Can change path |
| Theme selection | `test_theme_toggle` | Dark/light works |
| API key management | `test_api_key_secure` | Stored securely |

**Branch:** `um/feature/phase2-settings`

---

### Step 2.4: Keyboard Shortcuts

| Task | Test | Acceptance Criteria |
|------|------|---------------------|
| Command palette (Cmd+K) | `test_cmd_k` | Opens palette |
| Save (Cmd+S) | `test_cmd_s` | Saves file |
| New daily note (Cmd+D) | `test_cmd_d` | Creates note |

**Branch:** `um/feature/phase2-shortcuts`

---

### Phase 2 Completion Checklist

- [ ] Dashboard shows weekly activity
- [ ] Metrics trends visualized
- [ ] Settings panel functional
- [ ] Dark mode works
- [ ] Keyboard shortcuts work
- [ ] All tests passing

**Release:** Tag `v0.3.0-rc` on `um/main`

---

## Phase 3: Distribution

**Goal:** Packaged Electron app ready for use

### Step 3.1: Electron Integration

| Task | Test | Acceptance Criteria |
|------|------|---------------------|
| Add Electron to project | `npm run electron:dev` | App opens |
| Main process setup | N/A | Window creates |
| Preload scripts | N/A | IPC works |
| Python sidecar start | `test_sidecar_starts` | Backend runs |

**Branch:** `um/feature/phase3-electron`

---

### Step 3.2: Build & Package

| Task | Test | Acceptance Criteria |
|------|------|---------------------|
| electron-builder config | N/A | Config valid |
| macOS .dmg build | Manual test | DMG installs |
| Windows installer | Manual test | Installer works |
| Linux AppImage | Manual test | AppImage runs |

**Branch:** `um/feature/phase3-packaging`

---

### Step 3.3: Python Bundling

| Task | Test | Acceptance Criteria |
|------|------|---------------------|
| PyInstaller config | Build succeeds | Binary created |
| Include dependencies | App runs | No missing modules |
| Cross-platform builds | Test on each OS | All work |

**Branch:** `um/feature/phase3-python-bundle`

---

### Phase 3 Completion Checklist

- [ ] Electron app runs in dev
- [ ] macOS DMG builds and installs
- [ ] Windows installer works
- [ ] Linux AppImage runs
- [ ] Python backend bundled
- [ ] All features work in packaged app

**Release:** Tag `v1.0.0` on `um/main`

---

## CI/CD Pipeline

### GitHub Actions Workflow

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [um/main]
  pull_request:
    branches: [um/main]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.14'
      - run: |
          cd backend
          pip install -e ".[dev]"
          pytest --cov

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
      - run: |
          cd frontend
          npm ci
          npm run test
          npm run build

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: |
          cd backend && ruff check .
          cd ../frontend && npm run lint
```

---

## Test Coverage Requirements

| Component | Minimum Coverage |
|-----------|-----------------|
| Backend API | 80% |
| Storage Layer | 90% |
| Claude Client | 70% (mocked) |
| DuckDB Queries | 85% |
| Frontend Components | 70% |
| E2E Flows | Key paths covered |

---

## Review Checklist

Use this checklist for every PR:

### Code Quality
- [ ] Code follows project style guide
- [ ] No commented-out code
- [ ] Functions are small and focused
- [ ] Names are descriptive

### Testing
- [ ] New code has tests
- [ ] All tests pass
- [ ] Edge cases covered
- [ ] Mocks are appropriate

### Security
- [ ] No secrets in code
- [ ] Input validated
- [ ] SQL injection prevented (parameterized queries)
- [ ] API errors don't leak internals

### Documentation
- [ ] Complex code has comments
- [ ] API endpoints documented
- [ ] README updated if needed

---

*Back to: [README.md](./README.md)*
