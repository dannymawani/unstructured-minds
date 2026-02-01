# 05 - LLM Integration (Claude)

## Overview

Claude is the **optional** intelligence layer. The core app works fully without it.

| Without Claude | With Claude |
|----------------|-------------|
| View/edit markdown notes | Automatic extraction |
| File browser | Natural language queries |
| Manual data entry via forms | AI-powered skill execution |
| Direct SQL queries | Smart suggestions |
| Dashboard visualizations | Schema inference |

---

## Model Selection

| Task | Model | Model ID |
|------|-------|----------|
| Data Extraction | Haiku 4.5 | `claude-haiku-4-5-20251001` |
| Text-to-SQL | Haiku 4.5 | `claude-haiku-4-5-20251001` |
| Complex Skills | Sonnet 4.5 | `claude-sonnet-4-5-20250929` |

---

## Claude Client

```python
from anthropic import Anthropic

class ClaudeClient:
    def __init__(self):
        self.client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self.model_fast = "claude-haiku-4-5-20251001"
        self.model_smart = "claude-sonnet-4-5-20250929"

    async def extract(self, content: str, schema: dict) -> dict:
        """Extract structured data using tool use."""
        response = await self.client.messages.create(
            model=self.model_fast,
            max_tokens=4096,
            tools=[extraction_tool(schema)],
            messages=[{"role": "user", "content": content}]
        )
        return parse_tool_response(response)

    async def query(self, question: str, context: str) -> str:
        """Answer a natural language question."""
        response = await self.client.messages.create(
            model=self.model_fast,
            max_tokens=2048,
            system=QUERY_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}]
        )
        return response.content[0].text

    async def execute_skill(self, skill, context: dict) -> dict:
        """Execute a skill with context."""
        response = await self.client.messages.create(
            model=self.model_smart,
            max_tokens=8192,
            system=skill.system_prompt,
            messages=[{"role": "user", "content": skill.format_prompt(context)}]
        )
        return skill.parse_response(response.content[0].text)
```

---

## Data Extraction

Uses **Claude tool use** for guaranteed JSON schema compliance.

```
File saved → Hash check → Parse markdown → Claude API (tool use) → Validate → Upsert DuckDB
```

**Trigger timing:** On file save with 2-second debounce.

---

## Text-to-SQL

```
User: "How many workouts this week?"
        │
        ▼
Claude generates SQL:
  SELECT COUNT(*) FROM activities
  WHERE date >= CURRENT_DATE - INTERVAL '7 days'
        │
        ▼
Validate (SELECT only, no mutations)
        │
        ▼
Execute on DuckDB → Format response
```

**SQL Validation:**
```python
def validate_query(sql: str) -> bool:
    sql_lower = sql.lower().strip()
    if not sql_lower.startswith('select'):
        return False
    dangerous = ['insert', 'update', 'delete', 'drop', 'alter', 'create']
    return not any(d in sql_lower for d in dangerous)
```

---

## Skill Execution

Skills defined in markdown files in `skills/` directory.

```
User: "/daily"
        │
        ▼
Load skill definition (daily.md)
        │
        ▼
Gather context (yesterday's note, calendar, template)
        │
        ▼
Call Claude API (Sonnet for complex skills)
        │
        ▼
Parse response → Write file → Open in editor
```

---

## Error Handling

```python
async def _call_with_retry(self, func, *args, **kwargs):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except anthropic.RateLimitError:
            await asyncio.sleep(2 ** attempt)
        except anthropic.APIError:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(1)
    raise Exception("Max retries exceeded")
```

---

## Configuration

- **API Key:** Stored in system keychain, entered via Settings panel
- **Streaming:** Yes for queries/skills, No for extraction (needs complete JSON)
- **Conversation history:** Session-based, cleared on restart

---

*Next: [06-IMPLEMENTATION.md](./06-IMPLEMENTATION.md)*
