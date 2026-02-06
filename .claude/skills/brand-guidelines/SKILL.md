---
name: brand-guidelines
description: Applies Unstructured Minds brand colors, typography, and visual identity to any artifact that benefits from consistent styling. Use when brand colors, style guidelines, visual formatting, or design standards apply.
user-invocable: false
---

# Unstructured Minds Brand Styling

## Overview

Official brand identity and style resources for Unstructured Minds. Apply these guidelines when creating UI components, documents, or any visual artifact.

**Keywords**: branding, visual identity, colors, typography, dark mode, light mode, design system, CSS variables

## Brand Guidelines

### Colors

**Primary Colors:**

- Dark: `#0f172a` — Primary text, dark backgrounds (slate-900)
- Light: `#f8fafc` — Light backgrounds, text on dark (slate-50)
- Mid Gray: `#94a3b8` — Secondary elements (slate-400)
- Light Gray: `#e2e8f0` — Subtle backgrounds, borders (slate-200)

**Accent Colors:**

- Teal: `#14b8a6` — Primary accent, CTAs, active states (teal-500)
- Amber: `#f59e0b` — Warnings, highlights, secondary accent (amber-500)
- Indigo: `#6366f1` — Links, tertiary accent (indigo-500)
- Rose: `#f43f5e` — Errors, destructive actions (rose-500)

**Semantic Colors:**

- Success: `#22c55e` — Completed, positive states (green-500)
- Info: `#3b82f6` — Informational, neutral highlights (blue-500)

### CSS Variable Naming Convention

```css
/* Light mode (default) */
--bg-primary: #f8fafc;
--bg-secondary: #e2e8f0;
--bg-surface: #ffffff;
--text-primary: #0f172a;
--text-secondary: #475569;
--text-muted: #94a3b8;
--accent-primary: #14b8a6;
--accent-secondary: #f59e0b;
--border-default: #e2e8f0;
--border-subtle: #f1f5f9;

/* Dark mode */
--bg-primary: #0f172a;
--bg-secondary: #1e293b;
--bg-surface: #1e293b;
--text-primary: #f8fafc;
--text-secondary: #cbd5e1;
--text-muted: #64748b;
--accent-primary: #2dd4bf;
--accent-secondary: #fbbf24;
--border-default: #334155;
--border-subtle: #1e293b;
```

### Typography

- **Headings**: Inter (with system-ui, -apple-system fallback)
- **Body Text**: Inter (with system-ui, -apple-system fallback)
- **Monospace/Code**: JetBrains Mono (with Fira Code, monospace fallback)
- **Editor Text**: Inter for WYSIWYG, JetBrains Mono for raw markdown

**Font Scale:**
- Display: 2.25rem (36px) / 700
- H1: 1.875rem (30px) / 700
- H2: 1.5rem (24px) / 600
- H3: 1.25rem (20px) / 600
- Body: 1rem (16px) / 400
- Small: 0.875rem (14px) / 400
- Caption: 0.75rem (12px) / 400

### Logo Concept

**Theme:** "Order from Chaos"

The logo should convey the transformation of unstructured thought into organized, productive output. Key visual elements:

- **Left side (chaos):** A tumbling/washing machine drum or brain hemisphere with swirling, messy elements — scattered notes, loose text, random thoughts
- **Right side (structure):** Clean data tables, organized lists, charts — the structured output
- **Transition:** The messy elements flow through a central transformation point and emerge organized
- **Style:** Line art / geometric, works at small sizes, single-color variant available
- **Colors:** Uses teal (`#14b8a6`) as the primary mark color against dark (`#0f172a`) or light (`#f8fafc`) backgrounds

### Icon Conventions

- **Library:** lucide-react (consistent with shadcn/ui)
- **Size:** 16px for inline, 20px for buttons, 24px for navigation
- **Stroke:** 1.5px default, 2px for emphasis
- **Color:** Inherits from `currentColor` unless semantically colored
