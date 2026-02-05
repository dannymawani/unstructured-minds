# Mobile Responsive Design

**Phase:** 4 - Advanced Features
**Priority:** Medium
**Status:** Not Started

## Description

Make the application fully functional on mobile devices with responsive layout and touch interactions.

## Tasks

- [ ] Responsive sidebar (drawer on mobile)
- [ ] Touch-friendly file tree
- [ ] Mobile editor layout
- [ ] Swipe gestures
- [ ] Bottom navigation on mobile
- [ ] PWA manifest
- [ ] Offline capability (basic)

## Acceptance Criteria

- Usable on iPhone/Android
- Sidebar becomes drawer
- Editor takes full width
- File tree accessible via menu
- No horizontal scrolling
- Touch targets 44px minimum

## Breakpoints

```css
/* Mobile first */
@media (min-width: 640px) { /* sm: tablet */ }
@media (min-width: 1024px) { /* lg: desktop */ }
```

## Layout Changes

**Desktop**: Sidebar | Editor | Chat (3-column)
**Tablet**: Sidebar | Editor (2-column, chat in drawer)
**Mobile**: Full-width editor, sidebar/chat in drawers

## PWA Features

- Add to home screen
- App icon
- Splash screen
- Basic offline (view cached notes)
