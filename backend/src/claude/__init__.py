"""Claude API client — now a thin re-export from the provider-agnostic llm module."""

from ..llm import LLMClient

# Backward compatibility alias
ClaudeClient = LLMClient

__all__ = ["ClaudeClient", "LLMClient"]
