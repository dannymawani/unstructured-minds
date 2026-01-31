# 01 - Product Vision

## The Problem

Personal knowledge management is fragmented:
- Notes live in one app, data in spreadsheets, todos in another
- Extracting insights requires manual effort
- Natural language thoughts don't automatically become structured data
- No unified view of your life's data

## The Solution

**Unstructured Minds** - Write naturally, query intelligently.

A desktop application where you write in markdown, and an AI assistant (Claude) automatically extracts structured data, enables natural language queries, and provides dashboards over your personal data warehouse.

## One-Liner

> "Your second brain with a SQL engine underneath."

---

## Core User Stories

### Daily Logging

```
As a user,
I want to write "Had oatmeal with blueberries for breakfast, then a 45min strength session"
So that it automatically logs to my food and exercise databases
```

### Natural Language Queries

```
As a user,
I want to ask "How many times did I train legs this month?"
So that I get an instant answer from my data
```

### Daily Note Workflow

```
As a user,
I want to click one button to create today's note
So that it pulls my calendar, rolls over incomplete tasks, and sets up my day
```

### Dashboards

```
As a user,
I want to see my weekly activity, habit streaks, and trends
So that I can track progress without manual spreadsheet work
```

### Skill Execution

```
As a user,
I want to type "/wod" and get a personalized workout recommendation
So that the app acts as my AI assistant, not just a note-taker
```

---

## Scope

### In Scope (MVP)

| Feature | Description |
|---------|-------------|
| Markdown Editor | Write and edit .md files |
| File Browser | Navigate vault structure |
| Daily Note Button | One-click daily note creation |
| Auto-Extraction | Parse notes → structured data on save |
| Natural Language Input | Chat interface for logging/queries |
| DuckDB Backend | Query engine for all structured data |
| Basic Dashboards | Activity, habits, metrics views |
| Claude Integration | Skills, extraction, queries |

### Out of Scope (Future)

| Feature | Why Deferred |
|---------|--------------|
| Mobile App | Focus on desktop first |
| Multi-user/Sync | Local-first simplicity |
| Git Integration | Nice-to-have, not core |
| Voice Input | Adds complexity |
| Local LLM | Claude API is sufficient for now |
| Plugin System | Build core first |

---

## Target User

**Primary:** You (Danny) - power user who wants to own their data

**Secondary (future):**
- Quantified-self enthusiasts
- Developers who like markdown + databases
- People frustrated with fragmented productivity tools

---

## Success Criteria for MVP

1. [ ] Can create daily note with one click
2. [ ] Writing "logged 100kg squat 3x5" auto-populates exercise database
3. [ ] Can ask "total training hours this week" and get answer
4. [ ] Dashboard shows weekly activity summary
5. [ ] All data stored locally in markdown + DuckDB
6. [ ] Works offline (except Claude API calls)

---

## What Makes This Different

| Existing Tools | Unstructured Minds |
|---------------|-------------------|
| Obsidian | Great editor, no built-in data layer |
| Notion | Cloud-dependent, limited queries |
| Logseq | Good for notes, weak on structured data |
| Spreadsheets | Structured but not natural language |
| ChatGPT | Conversational but no persistence |

**Our unique combo:** Markdown simplicity + SQL power + AI extraction

---

## Open Questions

1. Should the app read existing Obsidian vaults or start fresh?
2. How much of the current Python scripts should be rewritten vs wrapped?
3. Should we support multiple vaults?
4. What's the licensing model if this becomes a product?

---

*Next: [02-ARCHITECTURE.md](./02-ARCHITECTURE.md)*
