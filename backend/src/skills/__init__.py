"""Skills module for executing predefined tasks."""

from .base import Skill, SkillContext
from .daily import DailyNoteSkill
from .registry import SkillRegistry, get_default_registry

__all__ = [
    "Skill",
    "SkillContext",
    "DailyNoteSkill",
    "SkillRegistry",
    "get_default_registry",
]
