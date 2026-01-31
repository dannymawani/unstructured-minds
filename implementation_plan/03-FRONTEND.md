# 03 - Frontend Framework Comparison

## Requirements

| Requirement | Priority | Notes |
|-------------|----------|-------|
| Markdown editing | Must-have | WYSIWYG with raw mode toggle |
| File tree navigation | Must-have | Hierarchical vault browser |
| Chat/input interface | Must-have | Natural language input |
| Dashboard/charts | Must-have | Data visualization |
| Command palette | Should-have | Quick actions, /skills |
| Split panes | Should-have | Editor + preview or multiple files |
| Keyboard-first | Should-have | Power user experience |
| Theming (dark mode) | Should-have | Eye comfort |
| Mobile responsive | Nice-to-have | For potential web version |

---

## Framework Comparison

### React

**Maturity:** ★★★★★
**Ecosystem:** ★★★★★
**Performance:** ★★★★☆
**Learning curve:** ★★★★☆ (familiar)

```typescript
// Example component structure
src/
├── components/
│   ├── Editor/
│   │   ├── MarkdownEditor.tsx
│   │   └── EditorToolbar.tsx
│   ├── Sidebar/
│   │   ├── FileTree.tsx
│   │   └── FileItem.tsx
│   ├── Chat/
│   │   └── ChatInterface.tsx
│   └── Dashboard/
│       ├── DashboardView.tsx
│       └── charts/
├── hooks/
│   ├── useVault.ts
│   ├── useDuckDB.ts
│   └── useClaude.ts
├── stores/
│   └── appStore.ts (zustand)
└── App.tsx
```

**Pros:**
- You likely know React already
- Huge ecosystem of components
- Great TypeScript support
- Milkdown (MIT-licensed markdown editor) is React-compatible

**Cons:**
- Need to choose state management
- Bundle size can grow

**Recommended libraries:**
- State: Zustand (simple) or Jotai (atomic)
- Styling: Tailwind CSS
- Components: Radix UI (unstyled) or shadcn/ui

---

### Svelte / SvelteKit

**Maturity:** ★★★★☆
**Ecosystem:** ★★★☆☆
**Performance:** ★★★★★
**Learning curve:** ★★★☆☆

```svelte
<!-- Example component -->
<script lang="ts">
  import { onMount } from 'svelte';
  import { vault } from '$lib/stores';

  let content = '';

  onMount(() => {
    // Load initial file
  });
</script>

<div class="editor">
  <textarea bind:value={content} />
</div>
```

**Pros:**
- Smaller bundle size
- Built-in reactivity (no state library needed)
- Less boilerplate than React
- Compiled = fast

**Cons:**
- Smaller ecosystem
- TipTap works but React version is better maintained
- Fewer developers if you expand team

---

### Solid.js

**Maturity:** ★★★☆☆
**Ecosystem:** ★★☆☆☆
**Performance:** ★★★★★
**Learning curve:** ★★★☆☆

**Pros:**
- React-like syntax, better performance
- Fine-grained reactivity
- Small bundle

**Cons:**
- Smallest ecosystem
- Fewer component libraries
- Risky for production app

**Verdict:** Interesting but too risky for this project.

---

### Vue 3

**Maturity:** ★★★★★
**Ecosystem:** ★★★★☆
**Performance:** ★★★★☆
**Learning curve:** ★★★★☆

**Pros:**
- Great docs
- Good TypeScript support
- Composition API is clean

**Cons:**
- Less momentum than React
- TipTap React version is more active
- Different paradigm if coming from React

---

## Recommendation: React + TypeScript

**Why React:**
1. Milkdown markdown editor works great with React
2. Largest ecosystem for components we need
3. Likely already familiar
4. Great browser support
5. Easy to find help/examples

---

## Markdown Editor Comparison

### Milkdown (Selected)

**Type:** Plugin-based markdown editor built on ProseMirror
**Stars:** 9k+
**License:** MIT (fully open source, no paid tiers)

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

**Pros:**
- 100% MIT licensed - no paid features
- Clean plugin architecture
- Good markdown support
- Built on ProseMirror (solid foundation)
- React integration available

**Cons:**
- Smaller community than TipTap
- May need more custom work for advanced features

---

### TipTap (Rejected)

**Type:** ProseMirror-based WYSIWYG
**Stars:** 28k+
**License:** MIT core, but Pro features are paid

**Why rejected:**
- Pro extensions require paid license
- Want fully open source stack with no licensing concerns

---

### Monaco Editor

**Type:** VS Code's editor
**Stars:** 40k+
**License:** MIT

**Pros:**
- Extremely powerful
- Great for raw markdown editing
- Syntax highlighting, intellisense

**Cons:**
- Not WYSIWYG
- Large bundle size (~2MB)
- Overkill for note-taking

**Verdict:** Good for "raw mode" toggle, not primary editor.

---

### CodeMirror 6

**Type:** Code editor
**Stars:** 5k+
**License:** MIT

**Pros:**
- Lightweight
- Very customizable
- Good markdown mode

**Cons:**
- Not WYSIWYG
- More work to set up

---

## Editor Recommendation: Milkdown

**Primary:** Milkdown for WYSIWYG markdown editing
**Secondary:** Monaco for raw markdown mode (optional toggle, if needed)

---

## UI Component Libraries

### shadcn/ui (Recommended)

```bash
npx shadcn-ui@latest add button dialog dropdown-menu
```

**Pros:**
- Copy-paste components (you own the code)
- Built on Radix UI (accessible)
- Tailwind-based
- Highly customizable

**Cons:**
- Not a traditional npm package
- Need to maintain copied code

---

### Radix UI

**Pros:**
- Unstyled, accessible primitives
- shadcn/ui is built on this
- Use directly for more control

---

### Headless UI

**Pros:**
- From Tailwind team
- Simple and lightweight

**Cons:**
- Fewer components than Radix

---

## Dashboard / Charts

### Recharts (Recommended for simplicity)

```tsx
import { LineChart, Line, XAxis, YAxis } from 'recharts';

<LineChart data={workoutData}>
  <XAxis dataKey="date" />
  <YAxis />
  <Line dataKey="volume" />
</LineChart>
```

**Pros:**
- React-native
- Easy to use
- Good for common charts

---

### Observable Plot (Recommended for power)

```tsx
import * as Plot from '@observablehq/plot';

Plot.plot({
  marks: [
    Plot.line(data, {x: "date", y: "volume"})
  ]
})
```

**Pros:**
- Extremely flexible
- Great for data exploration
- D3-based but simpler

**Cons:**
- Slightly steeper learning curve

---

### Chart.js

**Pros:**
- Popular, well-documented
- Canvas-based (performant)

**Cons:**
- Not as React-friendly
- Less flexible than Observable

---

## Final Stack Recommendation

```
Frontend Stack:
├── Framework:      React 19 + TypeScript 5.x
├── Deployment:     Docker (nginx:alpine) - NO Electron
├── Build:          Vite 6.x
├── Styling:        Tailwind CSS 4.x
├── Components:     shadcn/ui (Radix primitives)
├── State:          Zustand 5.x
├── Data Fetching:  TanStack React Query 5.x
├── Editor:         Milkdown (MIT, plugin-based)
├── Charts:         Recharts 2.x
├── Icons:          Lucide React
└── File Tree:      react-arborist or custom
```

> **Note:** Pure web app served via nginx. No Electron wrapper needed - simpler, lighter, and containerized.

---

## Wireframe Concept

```
┌─────────────────────────────────────────────────────────────────┐
│  ☰  Unstructured Minds                    ⌘K  🔍  ⚙️           │
├─────────────────┬───────────────────────────────────────────────┤
│                 │                                               │
│  📁 Vault       │  # Daily Note - 2026-01-31                   │
│  ├── Daily-Notes│                                               │
│  │   └── 2026-01│  ## Tasks                                    │
│  ├── Training   │  - [ ] Review PRs                            │
│  └── Work       │  - [x] Morning workout                       │
│                 │                                               │
│  ─────────────  │  ## Log                                      │
│                 │  Had oatmeal for breakfast...                │
│  💬 Chat        │                                               │
│  ┌───────────┐  │                                               │
│  │ Type here │  │  ---                                         │
│  │ or /skill │  │  ### Workout                                 │
│  └───────────┘  │  | Exercise | Weight | Reps |                │
│                 │                                               │
├─────────────────┴───────────────────────────────────────────────┤
│  📊 Dashboard: Weekly Activity   [Week ▾]                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  ████  ██  ████  ██  ████  ░░  ░░                      │   │
│  │  Mon  Tue  Wed  Thu  Fri  Sat  Sun                      │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

*Next: [04-DATA-LAYER.md](./04-DATA-LAYER.md)*
