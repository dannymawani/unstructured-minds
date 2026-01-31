# 05 - LLM Integration (Claude)

## Overview

Claude serves as the "intelligence layer" that transforms unstructured input into structured output. It powers three core functions:

1. **Data Extraction** - Parse notes → structured data
2. **Skill Execution** - Run /commands with context
3. **Natural Language Queries** - Answer questions about your data

---

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   Editor     │  │   Chat Box   │  │   Command Palette    │  │
│  │  (on save)   │  │  (queries)   │  │   (/skills)          │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
└─────────┼─────────────────┼─────────────────────┼───────────────┘
          │                 │                     │
          ▼                 ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Claude Service                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  Extraction  │  │   Query      │  │   Skill              │  │
│  │  Handler     │  │   Handler    │  │   Handler            │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│                           │                                      │
│                    ┌──────┴──────┐                              │
│                    │ Anthropic   │                              │
│                    │ SDK Client  │                              │
│                    └─────────────┘                              │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │  Claude API     │
                   │  (Anthropic)    │
                   └─────────────────┘
```

---

## API Client Setup

### Python Implementation

```python
from anthropic import Anthropic
import os

class ClaudeClient:
    def __init__(self):
        self.client = Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY")
        )
        self.model_fast = "claude-3-5-haiku-20241022"  # Extraction, SQL - cheap & fast
        self.model_smart = "claude-sonnet-4-20250514"  # Complex reasoning

    async def extract(self, content: str, schema: dict) -> dict:
        """Extract structured data from markdown using Haiku (fast & cheap)."""
        response = await self.client.messages.create(
            model=self.model_fast,  # Haiku for extraction
            max_tokens=4096,
            system=EXTRACTION_SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": f"Extract data from:\n\n{content}\n\nSchema:\n{schema}"
            }]
        )
        return parse_json_response(response.content[0].text)

    async def query(self, question: str, context: str) -> str:
        """Answer a natural language question."""
        response = await self.client.messages.create(
            model=self.model_fast,  # Haiku for simple queries
            max_tokens=2048,
            system=QUERY_SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {question}"
            }]
        )
        return response.content[0].text

    async def execute_skill(self, skill: str, context: dict) -> dict:
        """Execute a skill with given context (uses smarter model for complex tasks)."""
        response = await self.client.messages.create(
            model=self.model_smart,  # Sonnet for complex skills
            max_tokens=8192,
            system=skill.system_prompt,
            messages=[{
                "role": "user",
                "content": skill.format_prompt(context)
            }]
        )
        return skill.parse_response(response.content[0].text)
```

---

## 1. Data Extraction

### When to Extract
- On file save (debounced, e.g., 2 seconds after last edit)
- On app startup (batch process changed files)
- On manual trigger (re-extract command)

### Extraction Flow

```
File saved
    │
    ▼
Hash file content
    │
    ▼
Check if hash matches extraction_log
    │
    ├── Match → Skip (no changes)
    │
    └── No match → Continue
            │
            ▼
        Parse markdown sections
            │
            ▼
        Build extraction prompt
            │
            ▼
        Call Claude API
            │
            ▼
        Validate response JSON
            │
            ▼
        Upsert to DuckDB
            │
            ▼
        Update extraction_log
```

### Optimizations

**Batching:** Group multiple files into single API call
```python
# Instead of 10 calls for 10 files
# Send one call with 10 file contents
```

**Caching:** Cache Claude responses by content hash
```python
# If same content was extracted before, reuse result
cache_key = hashlib.md5(content.encode()).hexdigest()
if cache_key in extraction_cache:
    return extraction_cache[cache_key]
```

**Incremental:** Only send changed sections
```python
# Detect which section changed (## Workout vs ## Tasks)
# Only ask Claude to re-extract that section
```

---

## 2. Natural Language Queries

### Query Types

| Type | Example | Approach |
|------|---------|----------|
| Data Query | "How many workouts this week?" | Generate SQL, execute on DuckDB |
| Knowledge Query | "What's my PR for deadlift?" | Search notes + DuckDB |
| Action Request | "Create a new note for tomorrow" | Execute action |
| Clarification | "What do you mean by that?" | Conversational |

### Text-to-SQL Pipeline

```
User: "How many times did I train legs this month?"
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  Claude System Prompt:                                          │
│  You are a SQL assistant for DuckDB. Generate queries for:      │
│  - exercise_log (id, activity_id, date, exercise_name, ...)     │
│  - activities (id, date, activity_type, duration_minutes, ...)  │
│  - daily_metrics (date, sleep_hours, mood, energy...)           │
│  Return ONLY the SQL query, no explanation.                     │
└─────────────────────────────────────────────────────────────────┘
                    │
                    ▼
Generated SQL:
SELECT COUNT(DISTINCT activity_id)
FROM exercise_log
WHERE date >= DATE_TRUNC('month', CURRENT_DATE)
  AND exercise_name IN ('squat', 'deadlift', 'leg press', 'lunges')
                    │
                    ▼
Execute on DuckDB → Result: 8
                    │
                    ▼
Format response: "You trained legs 8 times this month."
```

### Safety

```python
# Validate generated SQL before execution
def validate_query(sql: str) -> bool:
    sql_lower = sql.lower().strip()

    # Only allow SELECT
    if not sql_lower.startswith('select'):
        return False

    # Block dangerous operations
    dangerous = ['insert', 'update', 'delete', 'drop', 'alter', 'create']
    if any(d in sql_lower for d in dangerous):
        return False

    # Parse and validate with DuckDB
    try:
        duckdb.execute(f"EXPLAIN {sql}")
        return True
    except:
        return False
```

---

## 3. Skill Execution

### Skill Definition Format

Skills are defined in markdown files (similar to current `.claude/skills/`):

```markdown
# daily

Create or update today's daily note.

## System Prompt

You are a daily note assistant. Create a structured daily note with:
- Task rollover from yesterday
- Calendar events for today
- Workout section if scheduled
- Reflection prompts

## Context Required

- Previous day's note (for task rollover)
- Calendar events (if integrated)
- User's daily note template
- Current injuries/constraints

## Output Format

Return a complete markdown note ready to save.

## Example

(example input/output)
```

### Skill Execution Flow

```
User: "/daily"
      │
      ▼
Skill Engine finds daily.md skill definition
      │
      ▼
Gather required context:
  - Read yesterday's note
  - Get calendar events
  - Load template
  - Load injury config
      │
      ▼
Build prompt with context
      │
      ▼
Call Claude API
      │
      ▼
Parse response (extract note content)
      │
      ▼
Write to vault/Daily-Notes/2026-01/2026-01-31.md
      │
      ▼
Open in editor
```

---

## Model Selection

| Task | Model | Why |
|------|-------|-----|
| **Data Extraction** | claude-3-5-haiku | Fast, cheap, great for structured JSON output |
| Text-to-SQL | claude-3-5-haiku | Quick SQL generation |
| Simple Skills | claude-3-5-haiku | Standard tasks |
| Complex Queries | claude-sonnet-4-20250514 | Multi-step reasoning |
| Only if needed | claude-opus-4-20250514 | Expensive, rarely necessary |

> **Key Change:** Use **Haiku for extraction** - it's 10x cheaper than Sonnet and excellent at structured output tasks.

### Cost Estimation (with Haiku)

```
Daily usage estimate:
- 10 file extractions/day @ 1K tokens each = 10K input tokens
- 20 queries/day @ 500 tokens each = 10K input tokens
- 5 skill executions/day @ 2K tokens each = 10K input tokens
- Response tokens ~50% of input = 15K output tokens

Daily total: ~30K input + 15K output tokens

Haiku pricing:
- Input: $0.25/1M tokens → $0.0075/day
- Output: $1.25/1M tokens → $0.019/day
- Total: ~$0.03/day or ~$1/month

(vs ~$10/month with Sonnet for everything)
```

---

## Error Handling

```python
class ClaudeClient:
    async def _call_with_retry(self, func, *args, **kwargs):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except anthropic.RateLimitError:
                wait = 2 ** attempt
                await asyncio.sleep(wait)
            except anthropic.APIError as e:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(1)
        raise Exception("Max retries exceeded")
```

---

## Offline Mode (Future)

For offline functionality, consider:

1. **Response Caching**
   - Cache common extractions and queries
   - Serve from cache when offline

2. **Local Model Fallback**
   - Ollama integration for local inference
   - Use smaller models (Llama, Mistral) for basic tasks

3. **Queue System**
   - Queue operations when offline
   - Process queue when connection restored

```python
class OfflineAwareClient:
    def __init__(self):
        self.claude = ClaudeClient()
        self.cache = ResponseCache()
        self.queue = OfflineQueue()
        self.local_model = OllamaClient()  # Optional

    async def extract(self, content, schema):
        # Check cache first
        cached = self.cache.get(content, schema)
        if cached:
            return cached

        # Try Claude
        try:
            result = await self.claude.extract(content, schema)
            self.cache.set(content, schema, result)
            return result
        except ConnectionError:
            # Queue for later
            self.queue.add('extract', content, schema)
            # Use local model if available
            if self.local_model:
                return await self.local_model.extract(content, schema)
            raise OfflineError("Queued for later processing")
```

---

## Security Considerations

1. **API Key Storage**
   - Store in system keychain (not plain text)
   - Use environment variables as fallback

2. **Data Privacy**
   - Option to exclude certain files from Claude processing
   - Local-only mode for sensitive notes

3. **Prompt Injection**
   - Sanitize user input in prompts
   - Use structured prompts with clear boundaries

---

## Resolved Design Decisions

### Streaming
**Decision:** Yes - stream responses for queries and skill execution.
- Better UX for longer responses
- Users see output as it generates
- Extraction does not stream (waits for complete JSON)

### Conversation History
**Decision:** Session-based history, cleared on app restart.
- Previous messages included for context within a session
- No persistent storage of chat history
- Keeps context window manageable
- Privacy-friendly (no long-term storage)

### Tool Use for Extraction
**Decision:** Yes - use Claude's tool use feature for data extraction.
- Guarantees valid JSON schema compliance
- More reliable than plain prompting
- Schema defined as tool parameters
- Eliminates JSON parsing errors

### Rate Limiting
**Decision:** Exponential backoff with retry (already in error handling section).
- 3 retries with exponential backoff
- Graceful degradation when limits hit
- Queue system for offline/rate-limited scenarios (future)

---

*Next: [06-IMPLEMENTATION.md](./06-IMPLEMENTATION.md)*
