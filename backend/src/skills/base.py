"""Base skill definitions."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

from ..storage import StorageBackend


@dataclass
class SkillContext:
    """Context for skill execution."""

    storage: StorageBackend
    current_date: Optional[str] = None  # YYYY-MM-DD format
    user_input: Optional[str] = None


@dataclass
class SkillResult:
    """Result from skill execution."""

    success: bool
    message: str
    data: Optional[dict[str, Any]] = None
    file_path: Optional[str] = None


class Skill(ABC):
    """Base class for all skills."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Skill name used for invocation."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what the skill does."""
        pass

    @abstractmethod
    async def execute(self, context: SkillContext) -> SkillResult:
        """Execute the skill.

        Args:
            context: Execution context with storage and optional parameters

        Returns:
            Result of skill execution
        """
        pass
