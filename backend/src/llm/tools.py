"""Tool format conversion between Anthropic and OpenAI formats.

LiteLLM uses OpenAI-style tool definitions. The existing codebase uses
Anthropic-style definitions (with `input_schema`). This module converts
between them so existing tool definitions keep working.
"""

from typing import Any


def anthropic_to_openai_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert Anthropic-format tool definitions to OpenAI format.

    Anthropic format:
        {"name": "...", "description": "...", "input_schema": {...}}

    OpenAI format:
        {"type": "function", "function": {"name": "...", "description": "...", "parameters": {...}}}
    """
    return [_convert_tool(t) for t in tools]


def _convert_tool(tool: dict[str, Any]) -> dict[str, Any]:
    """Convert a single tool definition."""
    # Already in OpenAI format
    if "type" in tool and tool["type"] == "function":
        return tool

    return {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool.get("description", ""),
            "parameters": tool.get("input_schema", tool.get("parameters", {})),
        },
    }
