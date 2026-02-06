# Unstructured Minds -- Design Manual

> Single source of truth for all visual design decisions.
> Last updated: 2026-02-06

---

## Table of Contents

1. [Visual Identity](#1-visual-identity)
2. [Color Palette](#2-color-palette)
3. [Typography](#3-typography)
4. [Logo Concept Brief](#4-logo-concept-brief)
5. [Component Styling](#5-component-styling)
6. [Icon Conventions](#6-icon-conventions)
7. [Spacing & Layout](#7-spacing--layout)
8. [Motion & Animation](#8-motion--animation)

---

## 1. Visual Identity

### Brand Name

**Unstructured Minds**

### Tagline

**"Order from Chaos"**

### Mission Statement

Unstructured Minds transforms natural language notes into structured, queryable data. We believe that the most valuable insights hide inside unstructured thought -- daily journals, meeting notes, scattered observations. Our tool bridges the gap between freeform writing and organized knowledge by using AI extraction and a personal data warehouse, giving users the power to query their own lives in plain English.

### The "Why" Behind the Visual System

The visual identity embodies the core transformation the product performs: taking something messy, organic, and human (unstructured notes) and producing something clean, precise, and useful (structured data). Every design decision reinforces this duality:

- **Dark slate tones** ground the interface, providing a calm workspace that recedes behind the user's content.
- **Teal accents** represent the moment of transformation -- the active, intelligent layer where AI extracts meaning.
- **Clean typography and generous whitespace** signal that structure and clarity are the end goal.
- **Subtle animations** show data flowing from chaos to order, never distracting from the writing experience.

The overall aesthetic is **modern, utilitarian, and quietly intelligent** -- a tool that feels like it understands what you write.

---

## 2. Color Palette

### Primary Colors

| Name       | Hex       | RGB              | HSL                  | Tailwind Class | Usage                              |
|------------|-----------|------------------|----------------------|----------------|------------------------------------|
| Dark       | `#0f172a` | `rgb(15, 23, 42)` | `hsl(222, 47%, 11%)` | `slate-900`    | Primary text, dark backgrounds     |
| Light      | `#f8fafc` | `rgb(248, 250, 252)` | `hsl(210, 40%, 98%)` | `slate-50`     | Light backgrounds, text on dark    |
| Mid Gray   | `#94a3b8` | `rgb(148, 163, 184)` | `hsl(215, 20%, 65%)` | `slate-400`    | Secondary/muted elements           |
| Light Gray | `#e2e8f0` | `rgb(226, 232, 240)` | `hsl(214, 32%, 91%)` | `slate-200`    | Borders, subtle backgrounds        |

### Accent Colors

| Name   | Hex       | RGB                  | HSL                    | Tailwind Class | Usage                              |
|--------|-----------|----------------------|------------------------|----------------|------------------------------------|
| Teal   | `#14b8a6` | `rgb(20, 184, 166)`  | `hsl(174, 80%, 40%)`  | `teal-500`     | Primary accent, CTAs, active states |
| Amber  | `#f59e0b` | `rgb(245, 158, 11)`  | `hsl(38, 92%, 50%)`   | `amber-500`    | Warnings, highlights, secondary accent |
| Indigo | `#6366f1` | `rgb(99, 102, 241)`  | `hsl(239, 84%, 67%)`  | `indigo-500`   | Links, tertiary accent             |
| Rose   | `#f43f5e` | `rgb(244, 63, 94)`   | `hsl(347, 90%, 60%)`  | `rose-500`     | Errors, destructive actions        |

### Semantic Colors

| Name    | Hex       | RGB                  | Tailwind Class | Usage                              |
|---------|-----------|----------------------|----------------|------------------------------------|
| Success | `#22c55e` | `rgb(34, 197, 94)`   | `green-500`    | Completed, positive states         |
| Info    | `#3b82f6` | `rgb(59, 130, 246)`  | `blue-500`     | Informational, neutral highlights  |
| Warning | `#f59e0b` | `rgb(245, 158, 11)`  | `amber-500`    | Caution states (shared with Amber) |
| Error   | `#f43f5e` | `rgb(244, 63, 94)`   | `rose-500`     | Errors, failures (shared with Rose)|

### Light Mode Palette

```css
--bg-primary: #f8fafc;        /* Page background */
--bg-secondary: #e2e8f0;      /* Sidebar, inset areas */
--bg-surface: #ffffff;         /* Cards, panels, elevated surfaces */
--text-primary: #0f172a;       /* Headings, body text */
--text-secondary: #475569;     /* Descriptions, supporting text */
--text-muted: #94a3b8;         /* Placeholders, disabled text */
--accent-primary: #14b8a6;     /* Teal -- buttons, links, active indicators */
--accent-secondary: #f59e0b;   /* Amber -- badges, highlights */
--border-default: #e2e8f0;     /* Standard borders */
--border-subtle: #f1f5f9;      /* Very faint dividers */
```

### Dark Mode Palette

```css
--bg-primary: #0f172a;        /* Page background */
--bg-secondary: #1e293b;      /* Sidebar, inset areas */
--bg-surface: #1e293b;        /* Cards, panels, elevated surfaces */
--text-primary: #f8fafc;       /* Headings, body text */
--text-secondary: #cbd5e1;     /* Descriptions, supporting text */
--text-muted: #64748b;         /* Placeholders, disabled text */
--accent-primary: #2dd4bf;     /* Teal-400 -- brightened for dark bg contrast */
--accent-secondary: #fbbf24;   /* Amber-400 -- brightened for dark bg contrast */
--border-default: #334155;     /* Standard borders */
--border-subtle: #1e293b;      /* Very faint dividers */
```

### Contrast Ratios (WCAG 2.1)

All text/background combinations must meet **AA** (4.5:1 for normal text, 3:1 for large text). Target **AAA** (7:1) where practical.

| Combination                          | Ratio   | Rating |
|--------------------------------------|---------|--------|
| `#0f172a` on `#f8fafc` (dark on light) | 17.3:1  | AAA    |
| `#f8fafc` on `#0f172a` (light on dark) | 17.3:1  | AAA    |
| `#475569` on `#f8fafc` (secondary text, light) | 7.1:1   | AAA    |
| `#cbd5e1` on `#0f172a` (secondary text, dark) | 10.2:1  | AAA    |
| `#94a3b8` on `#f8fafc` (muted text, light) | 3.4:1   | AA-large |
| `#64748b` on `#0f172a` (muted text, dark) | 4.6:1   | AA     |
| `#14b8a6` on `#0f172a` (teal on dark) | 7.5:1   | AAA    |
| `#14b8a6` on `#f8fafc` (teal on light) | 2.3:1   | Use for large/bold only |
| `#2dd4bf` on `#0f172a` (teal-400 on dark) | 10.0:1  | AAA    |

### Color Usage Guidelines

- **Primary actions**: Teal (`#14b8a6` light / `#2dd4bf` dark). Use for the single most important action on any screen.
- **Secondary actions**: Use `bg-secondary` (muted background) with `text-secondary-foreground`. Never compete with teal.
- **Destructive actions**: Rose (`#f43f5e`). Always pair with a confirmation step.
- **Information hierarchy**: Use `text-primary` for headings and key data, `text-secondary` for descriptions, `text-muted` for metadata and timestamps.
- **Backgrounds**: Never stack more than two background levels (e.g., page -> card is fine; page -> card -> nested card is not).
- **Borders**: Use `border-default` for structural dividers. Use `border-subtle` only for decorative/optional separation.
- **Dark mode accents**: Always use the `-400` variants (brightened) of accent colors in dark mode for sufficient contrast.

---

## 3. Typography

### Font Families

**Headings & Body Text:**
```css
font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
```

**Monospace / Code:**
```css
font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'Source Code Pro', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
```

**Editor Context:**
- WYSIWYG mode: Inter (same as body)
- Raw markdown mode: JetBrains Mono (monospace)

### Type Scale

| Level    | Size (rem) | Size (px) | Weight | Line Height | Letter Spacing | Tailwind Class          |
|----------|-----------|-----------|--------|-------------|----------------|--------------------------|
| Display  | 2.25      | 36        | 700    | 1.2 (43px)  | -0.025em       | `text-4xl font-bold`     |
| H1       | 1.875     | 30        | 700    | 1.25 (38px) | -0.02em        | `text-3xl font-bold`     |
| H2       | 1.5       | 24        | 600    | 1.3 (31px)  | -0.015em       | `text-2xl font-semibold` |
| H3       | 1.25      | 20        | 600    | 1.4 (28px)  | -0.01em        | `text-xl font-semibold`  |
| H4       | 1.125     | 18        | 600    | 1.4 (25px)  | normal         | `text-lg font-semibold`  |
| Body     | 1         | 16        | 400    | 1.6 (26px)  | normal         | `text-base font-normal`  |
| Small    | 0.875     | 14        | 400    | 1.5 (21px)  | normal         | `text-sm font-normal`    |
| Caption  | 0.75      | 12        | 400    | 1.5 (18px)  | 0.01em         | `text-xs font-normal`    |

### Heading Hierarchy

```
Display (36px/700) -- Hero sections, landing page headline only
  H1 (30px/700) -- Page titles (one per page)
    H2 (24px/600) -- Major sections within a page
      H3 (20px/600) -- Subsections, card titles
        H4 (18px/600) -- Minor headings, group labels
          Body (16px/400) -- Paragraphs, list items, form labels
            Small (14px/400) -- Secondary info, helper text, table cells
              Caption (12px/400) -- Timestamps, metadata, footnotes
```

### Code Typography

- **Inline code**: JetBrains Mono at 0.875em (relative to parent), `bg-muted` background, `px-1 py-0.5 rounded` padding.
- **Code blocks**: JetBrains Mono at 14px, line-height 1.6, with syntax highlighting.
- **Editor raw mode**: JetBrains Mono at 16px (matches body size for comfortable editing).

### Typography Guidelines

- Headings use **negative letter-spacing** to feel tighter and more authoritative at large sizes.
- Body text uses **default letter-spacing** for maximum readability.
- Caption text uses **slight positive letter-spacing** to improve legibility at small sizes.
- Maximum content width for reading: **65-75 characters** (~680px at 16px body).
- Never use font weights below 400 (regular). For de-emphasis, use color (`text-muted`) instead.

---

## 4. Logo Concept Brief

### Concept: "Order from Chaos"

The logo visually represents Unstructured Minds' core value proposition: transforming chaotic, unstructured thought into organized, actionable data.

### Visual Description (Designer Handoff)

```
LEFT SIDE (Chaos):
  A brain hemisphere or tumbling drum (washing machine metaphor)
  filled with swirling, overlapping elements:
  - Scattered text fragments
  - Loose bullet points
  - Wavy handwriting lines
  - Random thoughts floating freely
  Elements are rotated, overlapping, varied in opacity.

CENTER (Transformation):
  A vertical threshold or funnel point where the chaos passes through.
  Could be represented as:
  - A narrow channel / bottleneck
  - A glowing teal line or portal
  - An abstract "processing" zone
  The teal accent color (#14b8a6) is concentrated here.

RIGHT SIDE (Structure):
  Clean, aligned, organized output:
  - Neat rows of a data table
  - Aligned bullet lists
  - A simple chart or graph outline
  - Grid/card layout
  Elements are evenly spaced, uniform in size, high contrast.
```

**Style Direction:**
- Line art / geometric construction
- Must work at very small sizes (favicon)
- Single-color variant required for monochrome contexts
- Clean enough to be recognizable at 16px
- Should feel "smart" not "cute"

### Size Variants

| Context         | Sizes           | Format           | Notes                                      |
|-----------------|-----------------|------------------|--------------------------------------------|
| Favicon         | 16x16, 32x32   | ICO, SVG, PNG    | Simplified mark only (no wordmark)         |
| Navigation bar  | 24px, 32px h    | SVG               | Mark only, or mark + abbreviated "UM"      |
| Full logo       | 40px+ height    | SVG               | Mark + "Unstructured Minds" wordmark       |
| Social / OG     | 1200x630        | PNG               | Full logo centered, with tagline optional  |

### Color Variants

| Variant         | Mark Color       | Wordmark Color   | Background        |
|-----------------|------------------|------------------|-------------------|
| Light BG        | `#14b8a6` (teal) | `#0f172a` (dark) | `#f8fafc` or white |
| Dark BG         | `#2dd4bf` (teal-400) | `#f8fafc` (light) | `#0f172a` (slate-900) |
| Monochrome dark | `#0f172a`        | `#0f172a`        | White / transparent |
| Monochrome light| `#f8fafc`        | `#f8fafc`        | Dark / transparent |

### Clear Space

Minimum clear space around the logo: **equal to the height of the mark** on all sides. No other elements (text, icons, borders) may intrude into this zone.

```
  ┌──────────────────────────────┐
  │         (clear space)        │
  │    ┌──────────────────┐      │
  │    │   LOGO + MARK    │      │
  │    └──────────────────┘      │
  │         (clear space)        │
  └──────────────────────────────┘
       ^ height of mark on all sides
```

### Minimum Size

- **Mark only**: 16px (below this, use favicon-optimized version)
- **Mark + wordmark**: 80px wide minimum (wordmark becomes illegible below this)
- **Never scale the logo disproportionately.** Always maintain aspect ratio.

---

## 5. Component Styling

All components use Tailwind CSS utility classes. The project uses a shadcn/ui-compatible CSS variable system with `class-variance-authority` (CVA) for variant management.

### Buttons

#### Primary Button (Teal CTA)

**Light Mode:**
```
Background:    #14b8a6 (teal-500)         -> bg-teal-500
Text:          #ffffff (white)             -> text-white
Hover:         #0d9488 (teal-600)          -> hover:bg-teal-600
Active:        #0f766e (teal-700)          -> active:bg-teal-700
Focus ring:    #14b8a6 / 50% opacity       -> focus-visible:ring-teal-500/50
Border radius: 0.375rem (6px)              -> rounded-md
Padding:       0.5rem 1rem (8px 16px)      -> px-4 py-2
Font:          14px / 500                   -> text-sm font-medium
```

**Dark Mode:**
```
Background:    #14b8a6 (teal-500)          -> dark:bg-teal-500
Text:          #ffffff (white)             -> dark:text-white
Hover:         #2dd4bf (teal-400)          -> dark:hover:bg-teal-400
Active:        #14b8a6 (teal-500)          -> dark:active:bg-teal-500
Focus ring:    #2dd4bf / 50% opacity       -> dark:focus-visible:ring-teal-400/50
```

#### Secondary Button

**Light Mode:**
```
Background:    #f1f5f9 (slate-100)         -> bg-slate-100
Text:          #0f172a (slate-900)         -> text-slate-900
Hover:         #e2e8f0 (slate-200)         -> hover:bg-slate-200
Border:        none
```

**Dark Mode:**
```
Background:    #1e293b (slate-800)         -> dark:bg-slate-800
Text:          #f8fafc (slate-50)          -> dark:text-slate-50
Hover:         #334155 (slate-700)         -> dark:hover:bg-slate-700
```

#### Ghost Button

**Light Mode:**
```
Background:    transparent
Text:          #0f172a (slate-900)         -> text-slate-900
Hover BG:      #f1f5f9 (slate-100)         -> hover:bg-slate-100
Hover text:    #0f172a                      -> hover:text-slate-900
```

**Dark Mode:**
```
Background:    transparent
Text:          #f8fafc (slate-50)          -> dark:text-slate-50
Hover BG:      #1e293b (slate-800)         -> dark:hover:bg-slate-800
Hover text:    #f8fafc                      -> dark:hover:text-slate-50
```

#### Destructive Button (Rose)

**Light Mode:**
```
Background:    #f43f5e (rose-500)          -> bg-rose-500
Text:          #ffffff (white)             -> text-white
Hover:         #e11d48 (rose-600)          -> hover:bg-rose-600
Active:        #be123c (rose-700)          -> active:bg-rose-700
Focus ring:    #f43f5e / 50%               -> focus-visible:ring-rose-500/50
```

**Dark Mode:**
```
Background:    #9f1239 (rose-800)          -> dark:bg-rose-800
Text:          #fecdd3 (rose-200)          -> dark:text-rose-200
Hover:         #be123c (rose-700)          -> dark:hover:bg-rose-700
```

#### Button Sizes

| Size    | Height  | Padding         | Tailwind              |
|---------|---------|------------------|-----------------------|
| `sm`    | 36px    | `px-3 py-1.5`   | `h-9 px-3 text-sm`   |
| `default` | 40px | `px-4 py-2`     | `h-10 px-4 text-sm`  |
| `lg`    | 44px    | `px-8 py-2.5`   | `h-11 px-8 text-base`|
| `icon`  | 40px    | centered         | `h-10 w-10`          |

#### Disabled State (All Variants)

```
Opacity:          50%                      -> disabled:opacity-50
Pointer events:   none                     -> disabled:pointer-events-none
Cursor:           not-allowed (via opacity)
```

### Cards & Surfaces

**Light Mode:**
```
Background:    #ffffff (white)             -> bg-white
Border:        #e2e8f0 (slate-200)         -> border border-slate-200
Border radius: 0.5rem (8px)               -> rounded-lg
Shadow:        0 1px 3px rgba(0,0,0,0.1)  -> shadow-sm
Padding:       1.5rem (24px)              -> p-6
```

**Dark Mode:**
```
Background:    #1e293b (slate-800)         -> dark:bg-slate-800
Border:        #334155 (slate-700)         -> dark:border-slate-700
Shadow:        0 1px 3px rgba(0,0,0,0.3)  -> dark:shadow-md (heavier to register)
```

**Card Header:**
```
Font:          H3 (20px/600)               -> text-xl font-semibold
Margin bottom: 0.5rem                      -> mb-2
```

**Card Description:**
```
Font:          Small (14px/400)            -> text-sm
Color:         text-muted (slate-400/500)  -> text-muted-foreground
```

### Input / Form Fields

**Light Mode:**
```
Background:    #ffffff (white)             -> bg-white
Border:        #e2e8f0 (slate-200)         -> border border-slate-200
Border radius: 0.375rem (6px)             -> rounded-md
Text:          #0f172a (slate-900)         -> text-slate-900
Placeholder:   #94a3b8 (slate-400)         -> placeholder:text-slate-400
Height:        40px                        -> h-10
Padding:       0.5rem 0.75rem              -> px-3 py-2
Font:          14px/400                    -> text-sm
Focus border:  #14b8a6 (teal-500)          -> focus:border-teal-500
Focus ring:    #14b8a6 / 20%              -> focus:ring-2 focus:ring-teal-500/20
```

**Dark Mode:**
```
Background:    #0f172a (slate-900)         -> dark:bg-slate-900
Border:        #334155 (slate-700)         -> dark:border-slate-700
Text:          #f8fafc (slate-50)          -> dark:text-slate-50
Placeholder:   #64748b (slate-500)         -> dark:placeholder:text-slate-500
Focus border:  #2dd4bf (teal-400)          -> dark:focus:border-teal-400
Focus ring:    #2dd4bf / 20%              -> dark:focus:ring-teal-400/20
```

**Validation States:**
```
Error border:    #f43f5e (rose-500)        -> border-rose-500
Error text:      #f43f5e (rose-500)        -> text-rose-500
Error bg tint:   #fef2f2 (rose-50)         -> bg-rose-50 (light) / dark:bg-rose-950
Success border:  #22c55e (green-500)       -> border-green-500
```

**Labels:**
```
Font:          14px/500                    -> text-sm font-medium
Color:         text-primary               -> text-slate-900 dark:text-slate-50
Margin bottom: 0.375rem (6px)             -> mb-1.5
```

### Navigation

**Top Navigation Bar:**
```
Height:        48-56px
Background:    bg-surface (white / slate-800)
Border:        border-b border-default
Padding:       px-4 py-2
```

**Navigation Tab (Active):**
```
Background:    bg-secondary               -> bg-slate-100 dark:bg-slate-800
Text:          text-primary               -> text-slate-900 dark:text-slate-50
Font:          14px/500                    -> text-sm font-medium
Border radius: 0.375rem                   -> rounded-md
```

**Navigation Tab (Inactive):**
```
Background:    transparent
Text:          text-muted                 -> text-slate-400 dark:text-slate-500
Hover BG:      bg-accent/50              -> hover:bg-slate-100/50
```

**Sidebar:**
```
Width:         256px (16rem)               -> w-64
Background:    bg-surface
Border:        border-r border-default
```

**Sidebar Tab Bar:**
```
Height:        44px min (touch target)
Border:        border-b
Active tab:    bg-accent, border-b-2 border-primary
Inactive tab:  text-muted-foreground, hover:bg-accent/50
Font:          12px/500                    -> text-xs font-medium
```

### Badges & Tags

**Default Badge:**
```
Background:    #f1f5f9 (slate-100)         -> bg-slate-100 dark:bg-slate-800
Text:          #475569 (slate-600)         -> text-slate-600 dark:text-slate-300
Font:          12px/500                    -> text-xs font-medium
Padding:       2px 8px                     -> px-2 py-0.5
Border radius: 9999px (full pill)          -> rounded-full
```

**Teal Badge (Active/Primary):**
```
Background:    #ccfbf1 (teal-100)          -> bg-teal-100 dark:bg-teal-900/30
Text:          #0f766e (teal-700)          -> text-teal-700 dark:text-teal-300
```

**Amber Badge (Warning):**
```
Background:    #fef3c7 (amber-100)         -> bg-amber-100 dark:bg-amber-900/30
Text:          #b45309 (amber-700)         -> text-amber-700 dark:text-amber-300
```

**Rose Badge (Error/Destructive):**
```
Background:    #ffe4e6 (rose-100)          -> bg-rose-100 dark:bg-rose-900/30
Text:          #be123c (rose-700)          -> text-rose-700 dark:text-rose-300
```

**Indigo Badge (Info/Links):**
```
Background:    #e0e7ff (indigo-100)        -> bg-indigo-100 dark:bg-indigo-900/30
Text:          #4338ca (indigo-700)        -> text-indigo-700 dark:text-indigo-300
```

### Modals & Dialogs

**Overlay:**
```
Background:    rgba(0, 0, 0, 0.5)         -> bg-black/50
Backdrop blur:  4px                        -> backdrop-blur-sm
Z-index:       50                          -> z-50
```

**Modal Container:**

**Light Mode:**
```
Background:    #ffffff                     -> bg-white
Border:        #e2e8f0                     -> border border-slate-200
Border radius: 0.75rem (12px)             -> rounded-xl
Shadow:        large                       -> shadow-xl
Max width:     32rem (512px) for standard  -> max-w-lg
              48rem (768px) for wide       -> max-w-3xl
Padding:       1.5rem (24px)              -> p-6
```

**Dark Mode:**
```
Background:    #1e293b (slate-800)         -> dark:bg-slate-800
Border:        #334155 (slate-700)         -> dark:border-slate-700
Shadow:        extra-large                 -> dark:shadow-2xl
```

**Modal Header:**
```
Font:          H3 (20px/600)               -> text-xl font-semibold
Margin bottom: 1rem                        -> mb-4
Close button:  Ghost icon button, top-right -> absolute top-4 right-4
```

**Modal Footer:**
```
Margin top:    1.5rem                      -> mt-6
Alignment:     right-aligned              -> flex justify-end gap-3
Border top:    optional for long modals    -> border-t pt-4
```

---

## 6. Icon Conventions

### Library

**lucide-react** -- consistent with the shadcn/ui ecosystem. All icons use the same visual weight and style (1.5px stroke, rounded joins, consistent optical sizing).

Install: `lucide-react` (already a project dependency).

### Size Scale

| Context            | Size   | Tailwind Class  | Usage                              |
|--------------------|--------|-----------------|------------------------------------|
| Inline / metadata  | 16px   | `w-4 h-4`      | Inline with small text, tags, timestamps |
| Button / control   | 20px   | `w-5 h-5`      | Inside buttons, form controls, list items |
| Navigation / header| 24px   | `w-6 h-6`      | Nav icons, section headers, empty states |

### Stroke Width

| Context    | Width | Notes                                       |
|------------|-------|---------------------------------------------|
| Default    | 1.5px | Standard weight for most contexts            |
| Emphasis   | 2px   | Navigation icons, primary actions, headers   |
| Fine       | 1px   | Rarely used; only for very dense UI (tables) |

### Color

Icons inherit `currentColor` by default. Only apply explicit color for semantic meaning:

- **Success**: `text-green-500` (e.g., check marks, completed states)
- **Error**: `text-rose-500` (e.g., alert triangles, failed states)
- **Warning**: `text-amber-500` (e.g., exclamation marks)
- **Info**: `text-blue-500` (e.g., info circles)
- **Active/Accent**: `text-teal-500` / `dark:text-teal-400` (e.g., active nav item)

### Common Icon Mappings

| Concept            | Icon Component     | Usage Context                         |
|--------------------|--------------------|---------------------------------------|
| Files / Notes      | `FileText`         | File tree items, note references      |
| Folders            | `FolderOpen`       | Expanded directories in file tree     |
| Folders (closed)   | `Folder`           | Collapsed directories in file tree    |
| Calendar / Dates   | `Calendar`         | Daily notes, date pickers, calendar view |
| Brain / Extraction | `Brain`            | AI extraction, processing indicators  |
| Database / DuckDB  | `Database`         | Data queries, schema management       |
| Chat / Messages    | `MessageSquare`    | Chat panel, AI conversation           |
| Kanban / Board     | `Kanban`           | Kanban view toggle                    |
| Dashboard          | `LayoutDashboard`  | Dashboard view toggle                 |
| Search             | `Search`           | Search modal, search inputs           |
| Settings           | `Settings`         | Settings panel                        |
| Tags               | `Hash`             | Tag panel, tag badges                 |
| Links / Backlinks  | `Link2`            | Backlinks panel, wiki-links           |
| Save               | `Save`             | Save actions                          |
| Edit               | `Pencil`           | Edit mode toggles                     |
| Delete             | `Trash2`           | Delete actions (use rose color)       |
| Add / Create       | `Plus`             | New file, new item                    |
| Close / Dismiss    | `X`                | Modal close, notification dismiss     |
| Menu / Hamburger   | `Menu`             | Mobile sidebar toggle                 |
| Chevron (expand)   | `ChevronRight`     | Collapsible sections, tree nodes      |
| Chevron (down)     | `ChevronDown`      | Expanded sections, dropdowns          |
| Dark mode          | `Moon`             | Theme toggle (switch to dark)         |
| Light mode         | `Sun`              | Theme toggle (switch to light)        |
| Loading            | `Loader2`          | Spinner (use with `animate-spin`)     |
| Check / Done       | `Check`            | Completed tasks, success confirmation |
| Alert              | `AlertTriangle`    | Warnings, caution states              |
| Info               | `Info`             | Informational tooltips, help text     |
| Copy               | `Copy`             | Copy-to-clipboard actions             |
| Download           | `Download`         | Export data, download files            |
| Upload             | `Upload`           | Import data, upload files              |
| Filter             | `Filter`           | Data filtering controls                |
| Sort               | `ArrowUpDown`      | Column sorting in tables               |
| Refresh            | `RefreshCw`        | Refresh/reload data                    |
| External link      | `ExternalLink`     | Opens in new tab/window                |

---

## 7. Spacing & Layout

### Base Unit

**4px (0.25rem)**

All spacing values are multiples of the 4px base unit. This creates consistent visual rhythm throughout the interface.

### Spacing Scale

| Token  | Value    | Pixels | Tailwind | Usage                                    |
|--------|----------|--------|----------|------------------------------------------|
| `0.5`  | 0.125rem | 2px    | `0.5`    | Hairline gaps, icon-text micro-adjust    |
| `1`    | 0.25rem  | 4px    | `1`      | Tight spacing within compact elements    |
| `1.5`  | 0.375rem | 6px    | `1.5`    | Label-to-input gap, inline padding       |
| `2`    | 0.5rem   | 8px    | `2`      | Default gap between related elements     |
| `3`    | 0.75rem  | 12px   | `3`      | Padding inside compact components        |
| `4`    | 1rem     | 16px   | `4`      | Standard component padding, section gaps |
| `5`    | 1.25rem  | 20px   | `5`      | Increased breathing room                 |
| `6`    | 1.5rem   | 24px   | `6`      | Card padding, modal padding              |
| `8`    | 2rem     | 32px   | `8`      | Section spacing, large gaps              |
| `10`   | 2.5rem   | 40px   | `10`     | Major section dividers                   |
| `12`   | 3rem     | 48px   | `12`     | Page-level vertical spacing              |
| `16`   | 4rem     | 64px   | `16`     | Hero sections, large vertical gaps       |

### Common Spacing Patterns

| Pattern                          | Value     | Tailwind        |
|----------------------------------|-----------|-----------------|
| Icon to label gap                | 8px       | `gap-2`         |
| Button group gap                 | 8px       | `gap-2`         |
| Form field vertical gap          | 16px      | `space-y-4`     |
| Card internal padding            | 24px      | `p-6`           |
| Card group gap                   | 16px      | `gap-4`         |
| Section vertical spacing         | 32px      | `space-y-8`     |
| Page edge padding (desktop)      | 16-24px   | `px-4 sm:px-6`  |
| Page edge padding (mobile)       | 12-16px   | `px-3 sm:px-4`  |
| Modal padding                    | 24px      | `p-6`           |
| Header height                    | 48-56px   | `py-2 sm:py-3`  |

### Page Layout Patterns

#### Primary Layout: Sidebar + Content + Panel

```
┌─────────────────────────────────────────────────────────────┐
│  Header (full width, border-b)                    56px      │
├──────────┬──────────────────────────┬───────────────────────┤
│          │                          │                       │
│ Sidebar  │    Main Content          │   Chat / Detail       │
│  256px   │    flex-1                │   Panel 320px         │
│  (w-64)  │                          │   (w-80)              │
│          │                          │                       │
│          │                          │                       │
│ border-r │                          │  border-l             │
├──────────┴──────────────────────────┴───────────────────────┤
│  (Mobile: bottom nav, 64px)                                 │
└─────────────────────────────────────────────────────────────┘
```

#### Dashboard / Full-Width Layout

```
┌─────────────────────────────────────────────────────────────┐
│  Header (full width)                                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Content area (flex-1, overflow-auto, bg-background)        │
│  Max content width: 1280px (max-w-7xl mx-auto)             │
│  Padding: px-4 sm:px-6 lg:px-8                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Responsive Breakpoints

| Breakpoint | Min Width | Tailwind Prefix | Target Devices                   |
|------------|-----------|-----------------|----------------------------------|
| Default    | 0px       | (none)          | Small phones (portrait)          |
| `sm`       | 640px     | `sm:`           | Large phones (landscape)         |
| `md`       | 768px     | `md:`           | Tablets (portrait)               |
| `lg`       | 1024px    | `lg:`           | Tablets (landscape), small laptop|
| `xl`       | 1280px    | `xl:`           | Desktop, large laptop            |
| `2xl`      | 1536px    | `2xl:`          | Wide desktop, external monitor   |

### Responsive Behavior

| Element         | Mobile (< 640px)          | Tablet (768-1023px)       | Desktop (>= 1024px)         |
|-----------------|---------------------------|---------------------------|-----------------------------|
| Sidebar         | Drawer (slide-in from left) | Drawer (slide-in from left) | Fixed sidebar (w-64)       |
| Chat panel      | Drawer (slide-up from bottom) | Drawer (slide-in from right) | Fixed panel (w-80)      |
| Navigation      | Bottom tab bar (fixed)    | Top header tabs           | Top header tabs             |
| Brand name      | Abbreviated "UM"          | Full "Unstructured Minds" | Full "Unstructured Minds"   |
| View tab labels | Icons only (bottom nav)   | Icons + text              | Icons + text                |
| Content padding | `px-3 py-2`              | `px-4 py-3`              | `px-4 py-4` or larger      |

### Touch Targets

On touch devices (`pointer: coarse`), all interactive elements must meet a minimum size of **44x44px** as per WCAG 2.5.5 Target Size. Use the utility class `min-w-[44px] min-h-[44px]` on mobile-facing buttons.

---

## 8. Motion & Animation

### Transition Durations

| Token    | Duration | Usage                                          |
|----------|----------|------------------------------------------------|
| `fast`   | 150ms    | Hover states, color changes, opacity shifts    |
| `normal` | 200ms    | Button presses, focus rings, small transforms  |
| `slow`   | 300ms    | Panels sliding in/out, modals appearing, drawers |

### Tailwind Duration Classes

```
transition-colors duration-150     /* Color-only transitions (hover, active) */
transition-all duration-200        /* Multi-property transitions */
transition-transform duration-300  /* Slide-in panels, expand/collapse */
transition-opacity duration-200    /* Fade in/out */
```

### Easing Curves

| Name          | CSS Value                          | Tailwind Class     | Usage                             |
|---------------|-------------------------------------|--------------------|-----------------------------------|
| Ease out      | `cubic-bezier(0.0, 0.0, 0.2, 1)`  | `ease-out`         | Elements entering the viewport    |
| Ease in       | `cubic-bezier(0.4, 0.0, 1, 1)`    | `ease-in`          | Elements leaving the viewport     |
| Ease in-out   | `cubic-bezier(0.4, 0.0, 0.2, 1)`  | `ease-in-out`      | Elements that move within view    |
| Spring        | `cubic-bezier(0.34, 1.56, 0.64, 1)` | (custom)         | Playful bounces (use sparingly)   |

**Default easing**: `ease-out` for most transitions. Elements should feel like they arrive confidently and leave quickly.

### Animation Patterns

**Fade In (modals, tooltips, popovers):**
```css
@keyframes fadeIn {
  from { opacity: 0; }
  to   { opacity: 1; }
}
/* duration: 200ms, easing: ease-out */
```

**Slide In from Left (sidebar drawer):**
```css
@keyframes slideInLeft {
  from { transform: translateX(-100%); }
  to   { transform: translateX(0); }
}
/* duration: 300ms, easing: ease-out */
```

**Slide In from Bottom (mobile chat drawer):**
```css
@keyframes slideInBottom {
  from { transform: translateY(100%); }
  to   { transform: translateY(0); }
}
/* duration: 300ms, easing: ease-out */
```

**Spin (loading indicator):**
```css
/* Use Tailwind's built-in: animate-spin */
/* Applied to Loader2 icon */
```

**Scale In (badges, notifications):**
```css
@keyframes scaleIn {
  from { transform: scale(0.95); opacity: 0; }
  to   { transform: scale(1); opacity: 1; }
}
/* duration: 200ms, easing: ease-out */
```

### When to Animate

**Always animate:**
- Modal/dialog open and close
- Drawer slide in and out
- Hover state changes on interactive elements (buttons, links, list items)
- Focus ring appearance
- Loading spinners
- Toast/notification entrance

**Never animate:**
- Page-level navigation (view switches should be instant)
- Text content changes (avoid flickering)
- Scroll position changes (let the browser handle native scrolling)
- Color theme toggle (switch instantly to avoid flash-of-wrong-theme)

**Animate with care:**
- Accordion expand/collapse (use if content is short; skip for very long sections)
- Skeleton loading placeholders (subtle pulse, never distracting)
- Data chart transitions (only on initial load, not on every filter change)

### Reduced Motion

Respect the user's `prefers-reduced-motion` setting. When reduced motion is preferred:
- Replace all slide/scale animations with instant opacity transitions (150ms fade)
- Disable the loading spinner animation (show a static indicator instead)
- Keep focus ring transitions (accessibility aid, not decorative)

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## Appendix: Quick Reference

### CSS Variable Map (Full)

```css
/* ===== LIGHT MODE (default) ===== */
:root {
  /* Backgrounds */
  --bg-primary: #f8fafc;
  --bg-secondary: #e2e8f0;
  --bg-surface: #ffffff;

  /* Text */
  --text-primary: #0f172a;
  --text-secondary: #475569;
  --text-muted: #94a3b8;

  /* Accents */
  --accent-primary: #14b8a6;
  --accent-secondary: #f59e0b;

  /* Borders */
  --border-default: #e2e8f0;
  --border-subtle: #f1f5f9;

  /* Semantic */
  --color-success: #22c55e;
  --color-info: #3b82f6;
  --color-warning: #f59e0b;
  --color-error: #f43f5e;

  /* Radii */
  --radius-sm: 0.25rem;   /* 4px */
  --radius-md: 0.375rem;  /* 6px */
  --radius-lg: 0.5rem;    /* 8px */
  --radius-xl: 0.75rem;   /* 12px */
  --radius-full: 9999px;  /* pill */
}

/* ===== DARK MODE ===== */
:root.dark {
  /* Backgrounds */
  --bg-primary: #0f172a;
  --bg-secondary: #1e293b;
  --bg-surface: #1e293b;

  /* Text */
  --text-primary: #f8fafc;
  --text-secondary: #cbd5e1;
  --text-muted: #64748b;

  /* Accents */
  --accent-primary: #2dd4bf;
  --accent-secondary: #fbbf24;

  /* Borders */
  --border-default: #334155;
  --border-subtle: #1e293b;

  /* Semantic */
  --color-success: #22c55e;
  --color-info: #3b82f6;
  --color-warning: #fbbf24;
  --color-error: #f43f5e;
}
```

### Tailwind Color Classes Cheat Sheet

| Purpose               | Light Mode Class          | Dark Mode Class              |
|-----------------------|---------------------------|------------------------------|
| Page background       | `bg-slate-50`             | `dark:bg-slate-900`         |
| Surface/Card BG       | `bg-white`                | `dark:bg-slate-800`         |
| Primary text          | `text-slate-900`          | `dark:text-slate-50`        |
| Secondary text        | `text-slate-600`          | `dark:text-slate-300`       |
| Muted text            | `text-slate-400`          | `dark:text-slate-500`       |
| Primary accent        | `text-teal-500`           | `dark:text-teal-400`        |
| Primary accent BG     | `bg-teal-500`             | `dark:bg-teal-500`          |
| Standard border       | `border-slate-200`        | `dark:border-slate-700`     |
| Subtle border         | `border-slate-100`        | `dark:border-slate-800`     |
| Destructive           | `bg-rose-500 text-white`  | `dark:bg-rose-800 dark:text-rose-200` |
