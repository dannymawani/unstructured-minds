"""Claude API client implementation."""

import asyncio
import json
import re
import os
from typing import Any, Optional

import anthropic
from anthropic import AsyncAnthropic


QUERY_SYSTEM_PROMPT = """You are a helpful assistant that answers questions about the user's personal data.
You have access to their notes, exercise logs, daily metrics, and tasks.
Answer concisely and accurately based on the context provided."""


DAILY_NOTE_POPULATE_SYSTEM_PROMPT = """You populate a daily note template with the user's answers from a wizard.

Rules:
- Return ONLY the complete markdown document. No explanations, no code fences.
- Preserve all headers and structure exactly as-is.
- Use standard markdown only. Never use Obsidian syntax like [[wikilinks]] or callouts.
- Fill in sections based on the provided answers.

Cleaning up user input:
- Users type quick, messy answers in the wizard. Clean them up into clear, actionable items.
- Capitalize the first word of each item. Fix obvious typos and grammar.
- Split run-on text into separate items (look for commas, "and", newlines).
- Remove filler words like "uh", "maybe", "I need to", "I should" — just state the task.
- Keep items concise but preserve the user's intent.
- Example: "finish the api thing, call dentist and also groceries" becomes:
  - [ ] Finish the API integration
  - [ ] Call dentist
  - [ ] Groceries

Workout section (### Workout):
- If workout is "Rest": replace the Type/Focus lines with just `- Rest day`
- Otherwise: set `- **Type**: {workout}` and `- **Focus**: {workout}`

Energy & Recovery section (### Energy & Recovery):
- Set `- Sleep: {sleep}/10`, `- Energy Level: {energy}/10`, `- Mood: {mood}/10`
- Leave `- Nutrition:` empty (user fills later)

Work section (## 💼 Work):
- Parse the work priorities text into `- [ ]` checkbox items (clean up as described above)

Personal section (## 🤷🏽 Personal):
- Parse personal items into `- [ ]` checkbox items (clean up as described above)

Today's Focus section (## 🎯 Today's Focus):
- Pick the top 3-4 items from work + personal combined as `- [ ]` checkboxes

Adhoc Notes section (## 📝 Adhoc Notes):
- Parse adhoc text into `- item` bullet points (no checkboxes)
- If empty, leave as `- `"""


NOTE_ASSIST_SYSTEM_PROMPT = """You are a note assistant that helps the user edit and update their markdown notes.
You can see the current note content and help the user add, modify, or reorganize information.

When the user asks you to update the note (add a task, log a meal, record a workout, etc.),
return the full updated note content wrapped in <note-update>...</note-update> tags.
Outside the tags, provide a brief conversational reply explaining what you changed.

If the user is just asking a question about the note (not requesting changes), respond normally without the tags.

Rules for note updates:
- Preserve all existing content and formatting
- Add new content in the appropriate section
- Follow the existing markdown style and structure of the note
- If the note has frontmatter (---), keep it intact
- If the relevant section doesn't exist, create it in a logical position

Daily note section mapping — place content in the correct section:
- Tasks and to-dos → ## 🎯 Today's Focus (use `- [ ] description` checkbox format)
- Quick notes, random thoughts, captures → ## 📝 Adhoc Notes (use `- item` format)
- Work items, meetings, projects → ## 💼 Work
- Personal items, errands, life admin → ## 🤷🏽 Personal
- Workouts → ## 🏋️ Training & Health > ### Workout (use structured format: **Type**, **Focus**, then sets/reps)
- Sleep, energy, nutrition ratings → ## 🏋️ Training & Health > ### Energy & Recovery (use `X/10` rating format)

Formatting guidelines:
- Workouts: `- **Type**: Strength` / `- **Focus**: Upper Body` / then `- Exercise: sets x reps @ weight`
- Meals: `- Meal name: description, ~calories cal (P/C/F: Xg/Xg/Xg)` if the user provides macros
- Tasks: `- [ ] description` (always use checkbox format)
- Sleep/Energy/Nutrition: `Sleep: 7.5h (8/10)` or just `Sleep: 8/10`"""


class ClaudeClient:
    """Client for interacting with Claude API using async SDK."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        """Initialize Claude client.

        Args:
            api_key: Anthropic API key. If not provided, uses ANTHROPIC_API_KEY env var.
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._client: Optional[AsyncAnthropic] = None
        self.model_fast = "claude-haiku-4-5-20251001"
        self.model_smart = "claude-sonnet-4-5-20250929"

    @property
    def client(self) -> AsyncAnthropic:
        """Get or create async Anthropic client."""
        if self._client is None:
            if not self.api_key:
                raise ValueError("ANTHROPIC_API_KEY not configured")
            self._client = AsyncAnthropic(api_key=self.api_key)
        return self._client

    @property
    def is_configured(self) -> bool:
        """Check if client has API key configured."""
        return bool(self.api_key)

    async def extract(self, content: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Extract structured data from content using tool use.

        Args:
            content: Markdown content to extract from
            schema: JSON schema defining expected structure

        Returns:
            Extracted data as dictionary
        """
        tool = self._create_extraction_tool(schema)

        response = await self._call_with_retry(
            model=self.model_fast,
            max_tokens=4096,
            tools=[tool],
            messages=[{"role": "user", "content": self._extraction_prompt(content, schema)}],
        )

        return self._parse_tool_response(response)

    async def query(self, question: str, context: str) -> str:
        """Answer a natural language question about user data.

        Args:
            question: User's question
            context: Relevant context (data, previous notes, etc.)

        Returns:
            Answer text
        """
        response = await self._call_with_retry(
            model=self.model_fast,
            max_tokens=2048,
            system=QUERY_SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
            ],
        )

        return response.content[0].text

    async def note_assist(
        self,
        message: str,
        file_path: str | None = None,
        file_content: str | None = None,
        images: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Assist with editing a note, with optional image support.

        Args:
            message: User's message/instruction
            file_path: Path of the current note
            file_content: Current markdown content of the note
            images: Optional list of {"data": base64, "media_type": "image/png"}

        Returns:
            Dict with "reply" (str) and optional "updated_content" (str or None)
        """
        # Build content array for multimodal support
        content_parts: list[dict[str, Any]] = []

        # Add images first if present
        if images:
            for img in images:
                content_parts.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": img["media_type"],
                        "data": img["data"],
                    },
                })

        # Build text prompt with note context
        text_parts = []
        if file_path:
            text_parts.append(f"Current file: {file_path}")
        if file_content:
            text_parts.append(f"Current note content:\n```markdown\n{file_content}\n```")
        text_parts.append(f"User request: {message}")

        content_parts.append({"type": "text", "text": "\n\n".join(text_parts)})

        response = await self._call_with_retry(
            model=self.model_smart,
            max_tokens=8192,
            system=NOTE_ASSIST_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": content_parts}],
        )

        response_text = response.content[0].text

        # Parse <note-update> tags from response
        match = re.search(r"<note-update>(.*?)</note-update>", response_text, re.DOTALL)

        if match:
            updated_content = match.group(1).strip()
            # Remove the tags from the reply
            reply = re.sub(r"<note-update>.*?</note-update>", "", response_text, flags=re.DOTALL).strip()
            return {"reply": reply, "updated_content": updated_content}

        return {"reply": response_text, "updated_content": None}

    async def populate_daily_note(
        self,
        template: str,
        answers: dict[str, Any],
        date: str,
    ) -> str:
        """Populate a daily note template with wizard answers using AI.

        Args:
            template: The raw daily note template markdown
            answers: Dict with keys: workout, sleep, energy, mood,
                     work_priorities, personal, adhoc
            date: Date string (YYYY-MM-DD)

        Returns:
            Fully populated markdown string
        """
        user_prompt = f"""Date: {date}

Template:
```markdown
{template}
```

Wizard answers:
- Workout: {answers.get('workout', 'Rest')}
- Sleep: {answers.get('sleep', '')}/10
- Energy: {answers.get('energy', '')}/10
- Mood: {answers.get('mood', '')}/10
- Work priorities: {answers.get('work_priorities', '')}
- Personal items: {answers.get('personal', '')}
- Adhoc notes: {answers.get('adhoc', '')}

Populate the template with these answers and return only the complete markdown."""

        response = await self._call_with_retry(
            model=self.model_fast,
            max_tokens=4096,
            system=DAILY_NOTE_POPULATE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        return response.content[0].text

    async def execute_skill(
        self, system_prompt: str, user_prompt: str
    ) -> str:
        """Execute a skill with the smart model.

        Args:
            system_prompt: Skill's system prompt
            user_prompt: Formatted user prompt with context

        Returns:
            Skill response text
        """
        response = await self._call_with_retry(
            model=self.model_smart,
            max_tokens=8192,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        return response.content[0].text

    async def _call_with_retry(
        self, max_retries: int = 3, **kwargs
    ) -> Any:
        """Call the async API with exponential backoff retry.

        Args:
            max_retries: Maximum retry attempts
            **kwargs: Arguments passed to messages.create

        Returns:
            API response

        Raises:
            Exception: If max retries exceeded
        """
        last_error = None
        for attempt in range(max_retries):
            try:
                return await self.client.messages.create(**kwargs)
            except anthropic.RateLimitError as e:
                last_error = e
                await asyncio.sleep(2**attempt)
            except anthropic.APIError as e:
                last_error = e
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(1)

        raise Exception(f"Max retries exceeded: {last_error}")

    def _create_extraction_tool(self, schema: dict[str, Any]) -> dict[str, Any]:
        """Create extraction tool definition from schema.

        Args:
            schema: JSON schema for extraction

        Returns:
            Tool definition for Claude
        """
        return {
            "name": "extract_data",
            "description": "Extract structured data from the content",
            "input_schema": schema,
        }

    def _extraction_prompt(self, content: str, schema: dict[str, Any]) -> str:
        """Create extraction prompt.

        Args:
            content: Content to extract from
            schema: Expected schema

        Returns:
            Formatted prompt
        """
        return f"""Extract structured data from the following content.
Use the extract_data tool to return the data.

Content:
{content}
"""

    def _parse_tool_response(self, response: anthropic.types.Message) -> dict[str, Any]:
        """Parse tool use response to get extracted data.

        Args:
            response: Claude API response

        Returns:
            Extracted data dictionary
        """
        for block in response.content:
            if block.type == "tool_use":
                return block.input

        # Fallback: try to parse text as JSON
        for block in response.content:
            if block.type == "text":
                try:
                    return json.loads(block.text)
                except json.JSONDecodeError:
                    pass

        return {}
