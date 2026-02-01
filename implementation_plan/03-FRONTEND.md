# 03 - Frontend Specification

## Requirements

| Requirement | Priority |
|-------------|----------|
| Markdown editing (WYSIWYG) | Must-have |
| File tree navigation | Must-have |
| Chat/input interface | Must-have |
| Dashboard/charts | Must-have |
| Command palette (Cmd+K) | Should-have |
| Keyboard shortcuts | Should-have |
| Dark mode | Should-have |

---

## Technology Stack

```
Frontend Stack:
├── Framework:      React 19 + TypeScript 5.x
├── Build:          Vite 6.x
├── Deployment:     Docker (nginx:alpine)
├── Styling:        Tailwind CSS 4.x
├── Components:     shadcn/ui (Radix primitives)
├── State:          Zustand 5.x
├── Data Fetching:  TanStack React Query 5.x
├── Editor:         Milkdown 7.x (MIT, ProseMirror-based)
├── Charts:         Recharts 2.x
├── Icons:          Lucide React
└── File Tree:      react-arborist or custom
```

---

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── Editor/
│   │   │   ├── MarkdownEditor.tsx
│   │   │   └── EditorToolbar.tsx
│   │   ├── Sidebar/
│   │   │   ├── FileTree.tsx
│   │   │   └── FileItem.tsx
│   │   ├── Chat/
│   │   │   └── ChatInterface.tsx
│   │   └── Dashboard/
│   │       ├── DashboardView.tsx
│   │       └── charts/
│   ├── hooks/
│   │   ├── useVault.ts
│   │   ├── useDuckDB.ts
│   │   └── useClaude.ts
│   ├── stores/
│   │   └── appStore.ts
│   └── App.tsx
├── Dockerfile
├── nginx.conf
├── package.json
└── vite.config.ts
```

---

## Core Components

### Milkdown Editor

```typescript
import { Editor, rootCtx } from '@milkdown/core';
import { commonmark } from '@milkdown/preset-commonmark';
import { nord } from '@milkdown/theme-nord';
import { ReactEditor, useEditor } from '@milkdown/react';

const MilkdownEditor = () => {
  const { editor } = useEditor((root) =>
    Editor.make()
      .config((ctx) => {
        ctx.set(rootCtx, root);
      })
      .use(nord)
      .use(commonmark)
  );

  return <ReactEditor editor={editor} />;
};
```

### Charts (Recharts)

```tsx
import { LineChart, Line, XAxis, YAxis } from 'recharts';

<LineChart data={workoutData}>
  <XAxis dataKey="date" />
  <YAxis />
  <Line dataKey="volume" />
</LineChart>
```

### shadcn/ui Components

```bash
npx shadcn-ui@latest add button dialog dropdown-menu command
```

---

## Wireframe

```
┌─────────────────────────────────────────────────────────────────┐
│  ☰  Unstructured Minds                    Cmd+K  Search  Settings│
├─────────────────┬───────────────────────────────────────────────┤
│                 │                                               │
│  Vault          │  # Daily Note - 2026-01-31                   │
│  ├── Daily-Notes│                                               │
│  │   └── 2026-01│  ## Tasks                                    │
│  ├── Training   │  - [ ] Review PRs                            │
│  └── Work       │  - [x] Morning workout                       │
│                 │                                               │
│  ─────────────  │  ## Log                                      │
│                 │  Had oatmeal for breakfast...                │
│  Chat           │                                               │
│  ┌───────────┐  │                                               │
│  │ Type here │  │  ---                                         │
│  │ or /skill │  │  ### Workout                                 │
│  └───────────┘  │  | Exercise | Weight | Reps |                │
│                 │                                               │
├─────────────────┴───────────────────────────────────────────────┤
│  Dashboard: Weekly Activity   [Week ▾]                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  ████  ██  ████  ██  ████  ░░  ░░                      │   │
│  │  Mon  Tue  Wed  Thu  Fri  Sat  Sun                      │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

*Next: [04-DATA-LAYER.md](./04-DATA-LAYER.md)*
