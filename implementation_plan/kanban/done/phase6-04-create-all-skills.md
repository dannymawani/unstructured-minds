# Create All Background Skills

**Phase:** 6 - Before Starting
**Priority:** High
**Status:** Done
**Completed:** 2026-02-06
**Depends On:** phase6-01

## Description

Create all 7 new skills in `.claude/skills/`: brand-guidelines, design-manual, data-integration, performance-optimization, editor-ux, task-integration, dev-workflow.

## Tasks

- [x]Create data-integration skill documenting migration strategy
- [x]Create performance-optimization skill with three-tier save model
- [x]Create editor-ux skill with template and toolbar specs
- [x]Create task-integration skill with API and sync specs
- [x]Create dev-workflow skill with mandatory process
- [x]Create design-manual invocable skill
- [x]Verify all skills have valid YAML frontmatter

## Acceptance Criteria

- All 7 skill directories and SKILL.md files exist
- 6 background skills have `user-invocable: false`
- 1 invocable skill (design-manual) has `user-invocable: true`
- All skills are auto-detected by Claude
