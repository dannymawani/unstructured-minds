"""Skill registry for managing available skills."""


from .base import Skill, SkillContext, SkillResult
from .daily import DailyNoteSkill


class SkillRegistry:
    """Registry for available skills."""

    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        """Register a skill.

        Args:
            skill: Skill instance to register
        """
        self._skills[skill.name] = skill

    def get(self, name: str) -> Skill | None:
        """Get a skill by name.

        Args:
            name: Skill name

        Returns:
            Skill if found, None otherwise
        """
        return self._skills.get(name)

    def list(self) -> list[dict[str, str]]:
        """List all registered skills.

        Returns:
            List of skill info dicts with name and description
        """
        return [
            {"name": skill.name, "description": skill.description}
            for skill in self._skills.values()
        ]

    async def execute(self, name: str, context: SkillContext) -> SkillResult:
        """Execute a skill by name.

        Args:
            name: Skill name
            context: Execution context

        Returns:
            Skill result

        Raises:
            KeyError: If skill not found
        """
        skill = self.get(name)
        if not skill:
            raise KeyError(f"Skill not found: {name}")
        return await skill.execute(context)


_default_registry: SkillRegistry | None = None


def get_default_registry() -> SkillRegistry:
    """Get the default skill registry with built-in skills.

    Returns:
        SkillRegistry with default skills registered
    """
    global _default_registry
    if _default_registry is None:
        _default_registry = SkillRegistry()
        _default_registry.register(DailyNoteSkill())
    return _default_registry
