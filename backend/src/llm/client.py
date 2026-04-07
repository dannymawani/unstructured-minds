"""Provider-agnostic LLM client using LiteLLM.

Supports Anthropic, OpenAI, Ollama, and 100+ other providers.
See https://docs.litellm.ai/docs/providers for the full list.
"""

import asyncio
import json
import logging
import os
import re
from typing import Any, Optional

import litellm

from .tools import anthropic_to_openai_tools

logger = logging.getLogger(__name__)

# Suppress LiteLLM's noisy logging
litellm.suppress_debug_info = True
logging.getLogger("LiteLLM").setLevel(logging.WARNING)

# ---------------------------------------------------------------------------
# Default models per provider
# ---------------------------------------------------------------------------

MODEL_DEFAULTS: dict[str, dict[str, str]] = {
    "anthropic": {
        "fast": "anthropic/claude-haiku-4-5-20251001",
        "smart": "anthropic/claude-sonnet-4-5-20250929",
    },
    "openai": {
        "fast": "openai/gpt-4o-mini",
        "smart": "openai/gpt-4o",
    },
    "ollama": {
        "fast": "ollama/llama3.2",
        "smart": "ollama/llama3.2",
    },
}


# ---------------------------------------------------------------------------
# System prompts (moved here from claude/client.py)
# ---------------------------------------------------------------------------

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

Carried Forward section (## Carried Forward):
- If carried-forward tasks are provided, insert a `## Carried Forward` section BEFORE `## 🎯 Today's Focus`
- Each task is a `- [ ]` checkbox
- Deadline formatting: overdue tasks get "(Overdue: Mon DD)", due-today get "(Due today)", upcoming get "(Mon DD)"
- Do NOT duplicate carried-forward items into Today's Focus — they are separate

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


class LLMClient:
    """Provider-agnostic LLM client.

    Uses LiteLLM under the hood to support Anthropic, OpenAI, Ollama,
    and 100+ other providers with a unified interface.
    """

    def __init__(
        self,
        provider: str | None = None,
        api_key: str | None = None,
        model_fast: str | None = None,
        model_smart: str | None = None,
    ) -> None:
        # Resolve provider
        self.provider = (
            provider
            or os.environ.get("LLM_PROVIDER")
            or self._detect_provider(api_key)
        )

        # Set API key in the way LiteLLM expects
        resolved_key = (
            api_key
            or os.environ.get("LLM_API_KEY")
            or os.environ.get("ANTHROPIC_API_KEY")
            or os.environ.get("OPENAI_API_KEY")
        )
        if resolved_key:
            self._set_provider_key(resolved_key)
        self._api_key = resolved_key

        # Resolve models
        defaults = MODEL_DEFAULTS.get(self.provider, MODEL_DEFAULTS["anthropic"])
        self.model_fast = (
            model_fast
            or os.environ.get("LLM_MODEL_FAST")
            or defaults["fast"]
        )
        self.model_smart = (
            model_smart
            or os.environ.get("LLM_MODEL_SMART")
            or defaults["smart"]
        )

        # Ensure model names include provider prefix for LiteLLM
        self.model_fast = self._ensure_prefix(self.model_fast)
        self.model_smart = self._ensure_prefix(self.model_smart)

        logger.info(
            "llm_client_initialized",
            extra={
                "provider": self.provider,
                "model_fast": self.model_fast,
                "model_smart": self.model_smart,
                "configured": self.is_configured,
            },
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_configured(self) -> bool:
        """Check if client has credentials configured."""
        if self.provider == "ollama":
            return True  # Ollama doesn't need an API key
        return bool(self._api_key)

    # ------------------------------------------------------------------
    # Public API — matches the old ClaudeClient interface
    # ------------------------------------------------------------------

    async def complete(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        max_retries: int = 3,
    ) -> "LLMResponse":
        """Send a completion request to the LLM.

        This is the core method that all other methods build on.
        Accepts Anthropic-format tools and converts them automatically.
        """
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": self._build_messages(messages, system),
            "max_tokens": max_tokens,
        }

        if tools:
            kwargs["tools"] = anthropic_to_openai_tools(tools)

        last_error = None
        for attempt in range(max_retries):
            try:
                response = await litellm.acompletion(**kwargs)
                return LLMResponse(response)
            except litellm.RateLimitError as e:
                last_error = e
                await asyncio.sleep(2**attempt)
            except litellm.APIError as e:
                last_error = e
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(1)

        raise Exception(f"Max retries exceeded: {last_error}")

    async def extract(self, content: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Extract structured data from content using tool use."""
        tool = {
            "name": "extract_data",
            "description": "Extract structured data from the content",
            "input_schema": schema,
        }

        response = await self.complete(
            model=self.model_fast,
            max_tokens=4096,
            tools=[tool],
            messages=[{"role": "user", "content": self._extraction_prompt(content, schema)}],
        )

        return response.parse_tool_call() or self._try_json_parse(response.text) or {}

    async def query(self, question: str, context: str) -> str:
        """Answer a natural language question about user data."""
        response = await self.complete(
            model=self.model_fast,
            max_tokens=2048,
            system=QUERY_SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
            ],
        )
        return response.text

    async def note_assist(
        self,
        message: str,
        file_path: str | None = None,
        file_content: str | None = None,
        images: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Assist with editing a note, with optional image support."""
        content_parts: list[dict[str, Any]] = []

        # Add images if present and provider supports them
        if images:
            for img in images:
                content_parts.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{img['media_type']};base64,{img['data']}",
                    },
                })

        # Build text
        text_parts = []
        if file_path:
            text_parts.append(f"Current file: {file_path}")
        if file_content:
            text_parts.append(f"Current note content:\n```markdown\n{file_content}\n```")
        text_parts.append(f"User request: {message}")

        content_parts.append({"type": "text", "text": "\n\n".join(text_parts)})

        response = await self.complete(
            model=self.model_smart,
            max_tokens=8192,
            system=NOTE_ASSIST_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": content_parts}],
        )

        response_text = response.text
        match = re.search(r"<note-update>(.*?)</note-update>", response_text, re.DOTALL)

        if match:
            updated_content = match.group(1).strip()
            reply = re.sub(r"<note-update>.*?</note-update>", "", response_text, flags=re.DOTALL).strip()
            return {"reply": reply, "updated_content": updated_content}

        return {"reply": response_text, "updated_content": None}

    async def populate_daily_note(
        self,
        template: str,
        answers: dict[str, Any],
        date: str,
    ) -> str:
        """Populate a daily note template with wizard answers."""
        # Build workout suggestion section if available
        workout_section = ""
        suggestion = answers.get("workout_suggestion")
        if suggestion and suggestion.get("exercises"):
            date_str = suggestion.get('date', '')
            lines = [
                "",
                f"> **Suggested Workout (from {date_str})** — edit below to log, or delete if skipping",
                "> ",
                "> | Exercise | Last | Suggested | Reps | Sets |",
                "> |----------|------|-----------|------|------|",
            ]
            for ex in suggestion["exercises"]:
                name = ex.get("display_name") or ex.get("exercise_name", "")
                last_w = f"{ex['weight_kg']}kg" if ex.get("weight_kg") and ex["weight_kg"] > 0 else "BW"
                sugg_w = f"{ex['suggested_weight_kg']}kg" if ex.get("suggested_weight_kg") else last_w
                reps = str(ex.get("reps")) if ex.get("reps") else "-"
                sets = str(ex.get("sets")) if ex.get("sets") else "-"
                lines.append(f"> | {name} | {last_w} | {sugg_w} | {reps} | {sets} |")
            lines.append("")
            lines.append("Insert this blockquote table after the Focus line in the Workout section.")
            workout_section = "\n".join(lines)

        # Build carried-forward section
        carried_section = ""
        rollover_tasks = answers.get("rollover_tasks")
        if rollover_tasks:
            lines = ["- Carried-forward tasks (insert as ## Carried Forward before Today's Focus):"]
            for task in rollover_tasks:
                desc = task["description"]
                dl_status = task.get("deadline_status")
                deadline = task.get("deadline")
                if dl_status == "overdue" and deadline:
                    lines.append(f"  - {desc} (overdue since {deadline})")
                elif dl_status == "due_today":
                    lines.append(f"  - {desc} (due today)")
                elif dl_status == "upcoming" and deadline:
                    lines.append(f"  - {desc} (due {deadline})")
                else:
                    lines.append(f"  - {desc}")
            carried_section = "\n".join(lines)

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
{workout_section}
{carried_section}

Populate the template with these answers and return only the complete markdown."""

        response = await self.complete(
            model=self.model_fast,
            max_tokens=4096,
            system=DAILY_NOTE_POPULATE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return response.text

    async def execute_skill(self, system_prompt: str, user_prompt: str) -> str:
        """Execute a skill with the smart model."""
        response = await self.complete(
            model=self.model_smart,
            max_tokens=8192,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return response.text

    async def classify_exercises(
        self,
        unmatched_names: list[str],
        known_canonical_names: list[str],
    ) -> dict[str, str]:
        """Classify unmatched exercise names into canonical categories."""
        if not unmatched_names:
            return {}

        tool = {
            "name": "classify_exercises",
            "description": "Classify exercise names into canonical categories",
            "input_schema": {
                "type": "object",
                "properties": {
                    "classifications": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "raw_name": {"type": "string"},
                                "canonical_name": {"type": "string"},
                                "reasoning": {"type": "string"},
                            },
                            "required": ["raw_name", "canonical_name", "reasoning"],
                        },
                    },
                },
                "required": ["classifications"],
            },
        }

        known_list = "\n".join(f"- {n}" for n in known_canonical_names) if known_canonical_names else "(none)"
        unmatched_list = "\n".join(f"- {n}" for n in unmatched_names)

        prompt = f"""Classify these exercise names. For each one, decide if it's a variant of an existing canonical exercise or a new exercise.

Rules:
- If it's semantically the same as a known exercise (e.g. "Triceps" = "Tricep Exercises" = "Triceps Exercises"), map to the existing canonical name.
- Generic entries like "Biceps exercises", "Chest exercises" should map to the base form (e.g. "Biceps", "Chest").
- If it's genuinely new, create a clean Title Case canonical name.
- Strip trailing words like "exercises", "workout", "training" when they add no specificity.

Known canonical exercises:
{known_list}

Unmatched exercise names to classify:
{unmatched_list}

Use the classify_exercises tool to return your classifications."""

        response = await self.complete(
            model=self.model_fast,
            max_tokens=4096,
            tools=[tool],
            messages=[{"role": "user", "content": prompt}],
        )

        result = response.parse_tool_call("classify_exercises")
        if result:
            return {c["raw_name"]: c["canonical_name"] for c in result.get("classifications", [])}
        return {}

    async def label_new_exercises(
        self,
        exercise_names: list[str],
        known_muscle_groups: list[str],
        known_categories: list[str],
    ) -> list[dict]:
        """Generate exercise definitions for new exercises."""
        if not exercise_names:
            return []

        tool = {
            "name": "label_exercises",
            "description": "Generate exercise definitions with muscle groups",
            "input_schema": {
                "type": "object",
                "properties": {
                    "exercises": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "key": {"type": "string"},
                                "display": {"type": "string"},
                                "muscle_groups": {"type": "array", "items": {"type": "string"}},
                                "category": {"type": "string"},
                                "recovery_hours": {"type": "integer"},
                                "is_exercise": {"type": "boolean"},
                            },
                            "required": ["key", "display", "muscle_groups", "category", "recovery_hours", "is_exercise"],
                        },
                    },
                },
                "required": ["exercises"],
            },
        }

        names_list = "\n".join(f"- {n}" for n in exercise_names)
        muscles = ", ".join(sorted(known_muscle_groups)) if known_muscle_groups else "(none)"
        categories = ", ".join(sorted(known_categories)) if known_categories else "(none)"

        prompt = f"""Classify these exercise names. For each, provide muscle groups, category, and recovery hours.

Use existing muscle group and category names where possible.
Set is_exercise=false for activities (walks, sauna, swimming, mobility, martial arts drills, etc.).

Muscle groups: {muscles}
Categories: {categories}

Exercises:
{names_list}

Use the label_exercises tool."""

        response = await self.complete(
            model=self.model_fast,
            max_tokens=4096,
            tools=[tool],
            messages=[{"role": "user", "content": prompt}],
        )

        result = response.parse_tool_call("label_exercises")
        if result:
            return result.get("exercises", [])
        return []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _detect_provider(self, api_key: str | None = None) -> str:
        """Detect provider from available API keys."""
        key = api_key or os.environ.get("LLM_API_KEY", "")
        if key.startswith("sk-ant-"):
            return "anthropic"
        if os.environ.get("ANTHROPIC_API_KEY"):
            return "anthropic"
        if key.startswith("sk-"):
            return "openai"
        if os.environ.get("OPENAI_API_KEY"):
            return "openai"
        # Default to anthropic for backward compat
        return "anthropic"

    def _set_provider_key(self, key: str) -> None:
        """Set the API key in the environment where LiteLLM expects it."""
        if self.provider == "anthropic" or key.startswith("sk-ant-"):
            os.environ["ANTHROPIC_API_KEY"] = key
        elif self.provider == "openai" or key.startswith("sk-"):
            os.environ["OPENAI_API_KEY"] = key
        # For other providers, LiteLLM reads from various env vars
        # or we can pass api_key directly. Set a generic fallback.
        os.environ.setdefault("LLM_API_KEY", key)

    def _ensure_prefix(self, model: str) -> str:
        """Ensure model name has a provider prefix for LiteLLM."""
        if "/" in model:
            return model
        return f"{self.provider}/{model}"

    def _build_messages(
        self, messages: list[dict[str, Any]], system: str | None
    ) -> list[dict[str, Any]]:
        """Build message list with optional system message prepended."""
        result = []
        if system:
            result.append({"role": "system", "content": system})
        result.extend(messages)
        return result

    def _extraction_prompt(self, content: str, schema: dict[str, Any]) -> str:
        """Create extraction prompt."""
        return f"""Extract structured data from the following content.
Use the extract_data tool to return the data.

For any food or meals mentioned, ALWAYS estimate calories and macronutrients
(protein_g, carbs_g, fat_g) based on typical serving sizes, even if the user
did not provide numbers. Use your nutritional knowledge to give reasonable estimates.

Content:
{content}
"""

    @staticmethod
    def _try_json_parse(text: str | None) -> dict[str, Any] | None:
        """Try to parse text as JSON (fallback for providers without tool use)."""
        if not text:
            return None
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return None


class LLMResponse:
    """Unified response wrapper for LiteLLM responses.

    Provides a consistent interface regardless of provider, mapping
    the OpenAI-format response to simple accessors.
    """

    def __init__(self, raw: Any) -> None:
        self._raw = raw
        self._message = raw.choices[0].message

    @property
    def text(self) -> str:
        """Get the text content of the response."""
        return self._message.content or ""

    @property
    def tool_calls(self) -> list[Any]:
        """Get tool calls from the response."""
        return self._message.tool_calls or []

    def parse_tool_call(self, name: str | None = None) -> dict[str, Any] | None:
        """Parse the first matching tool call's arguments.

        Args:
            name: Optional tool name to filter by. If None, returns first tool call.

        Returns:
            Parsed arguments dict, or None if no matching tool call.
        """
        for tc in self.tool_calls:
            if name is None or tc.function.name == name:
                args = tc.function.arguments
                if isinstance(args, str):
                    return json.loads(args)
                return args
        return None
