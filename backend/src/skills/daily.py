"""Daily note skill implementation."""

import logging
from datetime import datetime

from ..api.settings import resolve_daily_note_path
from ..templates.daily_note import render_daily_note
from .base import Skill, SkillContext, SkillResult

logger = logging.getLogger(__name__)


class DailyNoteSkill(Skill):
    """Skill for creating daily notes."""

    @property
    def name(self) -> str:
        return "daily"

    @property
    def description(self) -> str:
        return "Create a new daily note for today (or a specified date)"

    async def execute(self, context: SkillContext) -> SkillResult:
        """Create a daily note.

        If context.current_date is provided, uses that date.
        Otherwise uses today's date.

        Args:
            context: Execution context

        Returns:
            Result with created file path
        """
        # Determine the date
        if context.current_date:
            try:
                date = datetime.strptime(context.current_date, "%Y-%m-%d")
            except ValueError:
                return SkillResult(
                    success=False,
                    message=f"Invalid date format: {context.current_date}. Use YYYY-MM-DD.",
                )
        else:
            date = datetime.now()

        date_str = date.strftime("%Y-%m-%d")

        # Build the file path using configurable template
        file_path = resolve_daily_note_path(date_str)

        # Check if file already exists
        if await context.storage.exists(file_path):
            return SkillResult(
                success=True,
                message=f"Daily note for {date_str} already exists.",
                file_path=file_path,
            )

        # Try vault template first, fall back to hardcoded
        try:
            tpl_bytes = await context.storage.read("Templates/daily.md")
            content = tpl_bytes.decode("utf-8")
        except Exception:
            logger.debug("Vault template not found, using hardcoded fallback")
            content = render_daily_note()

        # Write the file
        await context.storage.write(file_path, content.encode("utf-8"))

        return SkillResult(
            success=True,
            message=f"Created daily note for {date_str}.",
            file_path=file_path,
            data={"date": date_str},
        )
