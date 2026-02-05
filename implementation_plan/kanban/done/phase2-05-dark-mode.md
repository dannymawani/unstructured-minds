# Dark Mode & Theming

**Phase:** 2 - Polish
**Priority:** Medium
**Status:** Done

## Description

Implement proper dark/light theme support with system preference detection and manual override.

## Tasks

- [ ] CSS custom properties for theme colors
- [ ] Dark mode color palette
- [ ] Light mode color palette
- [ ] System preference detection (prefers-color-scheme)
- [ ] Theme toggle in header
- [ ] Theme persistence
- [ ] Milkdown editor theme sync

## Acceptance Criteria

- Follows system preference by default
- Manual toggle overrides system
- No flash on page load
- Editor matches app theme
- Charts and visualizations themed

## Color Variables

```css
--background, --foreground
--card, --card-foreground
--primary, --primary-foreground
--muted, --muted-foreground
--accent, --accent-foreground
--border, --input, --ring
```

## Key Files

- `frontend/src/styles/themes.css`
- `frontend/src/hooks/useTheme.ts`
