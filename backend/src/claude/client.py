"""Claude API client implementation."""

import asyncio
import json
import os
from typing import Any, Optional

import anthropic
from anthropic import Anthropic


QUERY_SYSTEM_PROMPT = """You are a helpful assistant that answers questions about the user's personal data.
You have access to their notes, exercise logs, daily metrics, and tasks.
Answer concisely and accurately based on the context provided."""


class ClaudeClient:
    """Client for interacting with Claude API."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        """Initialize Claude client.

        Args:
            api_key: Anthropic API key. If not provided, uses ANTHROPIC_API_KEY env var.
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._client: Optional[Anthropic] = None
        self.model_fast = "claude-haiku-4-5-20251001"
        self.model_smart = "claude-sonnet-4-5-20250929"

    @property
    def client(self) -> Anthropic:
        """Get or create Anthropic client."""
        if self._client is None:
            if not self.api_key:
                raise ValueError("ANTHROPIC_API_KEY not configured")
            self._client = Anthropic(api_key=self.api_key)
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
            self._create_message,
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
            self._create_message,
            model=self.model_fast,
            max_tokens=2048,
            system=QUERY_SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
            ],
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
            self._create_message,
            model=self.model_smart,
            max_tokens=8192,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        return response.content[0].text

    def _create_message(self, **kwargs) -> anthropic.types.Message:
        """Create a message synchronously."""
        return self.client.messages.create(**kwargs)

    async def _call_with_retry(
        self, func, *args, max_retries: int = 3, **kwargs
    ) -> Any:
        """Call function with exponential backoff retry.

        Args:
            func: Function to call
            max_retries: Maximum retry attempts

        Returns:
            Function result

        Raises:
            Exception: If max retries exceeded
        """
        last_error = None
        for attempt in range(max_retries):
            try:
                # Run sync function in thread pool
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, lambda: func(*args, **kwargs))
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
