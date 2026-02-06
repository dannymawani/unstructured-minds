---
name: design-manual
description: Generate or update the DESIGN_MANUAL.md for Unstructured Minds. Covers visual identity, color palette, typography, logo brief, component styling, and icon conventions.
user-invocable: true
allowed-tools: Read, Write, Glob, Grep
---

# Generate Design Manual

Create or update the `DESIGN_MANUAL.md` file at the project root with the complete visual design system for Unstructured Minds.

## Process

1. Read the current brand-guidelines skill for source of truth
2. Read existing `DESIGN_MANUAL.md` if it exists (to preserve any manual additions)
3. Read `frontend/tailwind.config.js` and `frontend/src/index.css` for current theme values
4. Generate/update the design manual

## Output: DESIGN_MANUAL.md

The generated file must include all of the following sections:

### 1. Visual Identity
- Brand name, tagline ("Order from Chaos"), mission statement
- The "why" behind the visual system

### 2. Color Palette
- All colors with hex codes, RGB values, and Tailwind class names
- Light mode palette with contrast ratios
- Dark mode palette with contrast ratios
- Semantic colors (success, warning, error, info)
- Usage guidelines (when to use each color)

### 3. Typography
- Font families with full fallback stacks
- Type scale (display through caption) with sizes, weights, line heights
- Heading hierarchy examples
- Code/monospace font usage
- Editor-specific typography

### 4. Logo Concept Brief
- Concept: "Order from Chaos" — messy brain/tumbler → structured data
- Visual description for designer handoff
- Size variants needed (favicon, nav, full)
- Color variants (light bg, dark bg, monochrome)
- Clear space and minimum size rules

### 5. Component Styling
- Button variants (primary, secondary, ghost, destructive)
- Card/surface styling
- Input/form field styling
- Navigation patterns
- Badge/tag styling
- Modal/dialog styling
- All with light and dark mode

### 6. Icon Conventions
- Library: lucide-react
- Size scale (16/20/24px)
- Stroke width conventions
- Common icon mappings (file→FileText, folder→FolderOpen, etc.)

### 7. Spacing & Layout
- Base unit (4px / 0.25rem)
- Common spacing values
- Page layout patterns
- Responsive breakpoints

### 8. Motion & Animation
- Transition durations (fast: 150ms, normal: 200ms, slow: 300ms)
- Easing curves
- When to animate vs. not

## Arguments

$ARGUMENTS

- No args: Generate full design manual
- `--section <name>`: Update only a specific section
- `--audit`: Compare current CSS/Tailwind with the manual and report drift
