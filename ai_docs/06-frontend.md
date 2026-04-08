# Frontend

React patterns, component inventory, state management, Milkdown editor, and build pipeline.

## Tech Stack

React 19 + Vite 7 + TypeScript 5.9 (strict) + Tailwind v4 + Milkdown 7 + Clerk + lucide-react

## Views (Lazy-loaded)

1. **Editor** (`/`, `/editor`) — Milkdown markdown editor + sidebar + chat
2. **Dashboard** (`/dashboard`) — Configurable analytics widgets
3. **Kanban** (`/kanban`) — 4-column personal task board (Backlog → In Progress → Done → Cancelled)
4. **Calendar** (`/calendar`) — Monthly calendar with daily note indicators

## Component Inventory

**Layout:** Drawer (mobile slide-out), MobileNav (bottom tabs)

**Files:** FileTree (virtualized, nested), FileTreeItem (memoized)

**Editor:** MarkdownEditor (Milkdown), EditorToolbar (formatting buttons), EditorPlugins (slash menu, code block exit)

**Chat:** ChatPanel (AI assistant), ChatMessage (with query results table)

**Dashboard:** Dashboard, DashboardSummary, WeeklyActivityChart, MetricsTrends, ExerciseTable, ActivityHeatmap, SleepTrends, MoodCorrelation, NutritionTile, ExerciseProgress, EnduranceLog, EnduranceProgress, InsightsCard, WidgetConfig

**Tasks:** PersonalKanban, PersonalTaskCard (draggable), PersonalTaskModal

**Modals:** CommandPalette (Cmd+K), SearchModal, QuickCapture, TemplatePicker, SettingsPanel, DailyNoteWizard

**Calendar:** CalendarView

**UI:** Button (CVA variants), SchemaManager

## State Management (Hooks, No Global Store)

| Hook | Purpose |
|------|---------|
| `useUIState()` | Modal visibility, sidebar state, mobile drawers, wizard state |
| `useFileManager()` | File selection, content, autosave (60s), dirty tracking, save state |
| `useTheme()` | Light/dark mode (localStorage persisted, `.dark` class on root) |
| `useMobile()` | Responsive breakpoints: mobile (<640), tablet (640-1024), desktop (>=1024) |
| `useKeyboardShortcuts()` | Global keyboard listener |

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Cmd+S` | Save |
| `Cmd+K` | Command palette |
| `Cmd+B` | Toggle sidebar |
| `Cmd+D` | Today's daily note |
| `Cmd+Shift+F` | Search |
| `Cmd+Shift+N` | Quick capture |
| `Cmd+T` | New from template |

## API Client (`lib/apiClient.ts`)

- Base URL: `VITE_API_URL` (default `http://localhost:8000`, Docker: `/api`)
- **Global fetch interceptor** patches `window.fetch` to inject `Authorization: Bearer` header
- Token gate: Promise blocks requests until Clerk initializes (resolves immediately if no Clerk)
- Methods: `api.get<T>()`, `api.post<T>()`, `api.put<T>()`, `api.patch<T>()`, `api.delete<T>()`, `api.raw()` (SSE)

## Milkdown Editor

**Plugins:** commonmark, gfm (tables, strikethrough), history (undo/redo), listener (change events), slash menu (`/`), custom codeBlockExitPlugin (Mod-Enter)

**Toolbar:** Bold, Italic, Strikethrough, Code, H1-H3, Lists, Quote, Code Block, Divider, Table (interactive grid picker)

**Max-width:** 52rem | **Font:** Inter

## File Naming

- Components: `PascalCase.tsx`
- Hooks: `useCamelCase.ts`
- Utils: `camelCase.ts`
- Types: `types.ts` or `*.types.ts`

## CSS/Theming

- Tailwind v4 via `@tailwindcss/vite` (no postcss)
- Dark (default) / Light themes via CSS custom properties
- Dark BG: `#0f172a`, Light BG: `#f3f4f6`, Accent: `#14b8a6` (teal)
- Mobile-first responsive, 44px touch targets, safe area insets
- One change at a time — verify no regressions before the next edit

## Brand Quick Reference

| Color | Hex | Usage |
|-------|-----|-------|
| Teal | `#14b8a6` | Primary accent, CTAs |
| Dark | `#0f172a` | Dark backgrounds, primary text |
| Light | `#f8fafc` | Light backgrounds |
| Amber | `#f59e0b` | Warnings, highlights |
| Indigo | `#6366f1` | Links |
| Rose | `#f43f5e` | Errors |

See `brand-guidelines` skill for full design system.

## Build Pipeline

### Dev Commands
- `npm run dev` — Dev server with live type checking overlay (`vite-plugin-checker`)
- `npm run typecheck` — Standalone TS check (CI/manual)
- `npm run build` — `tsc -b && vite build` (production)
- `npm run analyze` — Bundle analysis

### Vite Config
- React plugin + Tailwind v4 plugin + vite-plugin-checker
- Path alias: `@/` → `./src/`
- API proxy: `/api` → backend
- Code splitting: vendor-react, vendor-milkdown, vendor-icons

### Docker Build
- Build: `node:22-alpine` → `npm ci && npm run build`
- Runtime: `nginx:alpine` serving `/usr/share/nginx/html`
- **`VITE_CLERK_PUBLISHABLE_KEY` must be a build arg** — Vite bakes `VITE_*` variables into the JS bundle at build time
- Healthcheck: `wget --spider http://localhost:80/`

## PWA

`manifest.json`: standalone display, `#0f172a` bg, `#14b8a6` theme, `um-icon.svg` icon

## Logo Assets

| File | Purpose | Served from |
|------|---------|-------------|
| `um-icon.svg` | Favicon, PWA icon (brain only) | `frontend/public/` |
| `um-logo.svg` | In-app branding (full logo) | `frontend/public/` |

Source files in `assets/images/` use kebab-case.

## Vault & Daily Notes

**Path pattern:** `vault/YYYY/MM/YYYY-MM-DD.md`

**Daily note template sections:** Adhoc Notes, Today's Focus, Carried Forward, Work, Personal, Training & Health (Workout + Energy & Recovery), Wins Today, Tomorrow's Priorities

**Frontmatter:** `date`, `type: daily-note`, `tags: [daily, journal]`
