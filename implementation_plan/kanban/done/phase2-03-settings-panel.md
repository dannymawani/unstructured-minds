# Settings Panel

**Phase:** 2 - Polish
**Priority:** High
**Status:** Done

## Description

Create a settings panel for configuring the application including vault path, theme, and API key management.

## Tasks

- [ ] Settings component with tabs/sections
- [ ] Vault path configuration
- [ ] Theme selection (dark/light/system)
- [ ] API key management (secure storage)
- [ ] Settings persistence API
- [ ] Import/export settings

## Acceptance Criteria

- Settings form renders with current values
- Changes persist across sessions
- Theme toggle works immediately
- API key never exposed in UI after entry

## API Endpoints

```
GET  /settings          -> Current settings
POST /settings          -> Update settings
GET  /settings/themes   -> Available themes
```

## UI Sections

1. **General** - Vault path, auto-save interval
2. **Appearance** - Theme, font size, editor width
3. **API Keys** - Anthropic key (masked)
4. **Advanced** - Debug mode, extraction settings
