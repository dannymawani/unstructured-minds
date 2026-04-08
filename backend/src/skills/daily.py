"""Daily note skill implementation."""

from datetime import datetime

from ..templates.daily_note import render_daily_note
from .base import Skill, SkillContext, SkillResult


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

        # Build the file path: Daily-Notes/YYYY-MM/YYYY-MM-DD.md
        year_month = date.strftime("%Y-%m")
        file_path = f"Daily-Notes/{year_month}/{date_str}.md"

        # Check if file already exists
        if await context.storage.exists(file_path):
            return SkillResult(
                success=True,
                message=f"Daily note for {date_str} already exists.",
                file_path=file_path,
            )

        # Render template
        content = render_daily_note(date_str)

        # Write the file
        await context.storage.write(file_path, content.encode("utf-8"))

        return SkillResult(
            success=True,
            message=f"Created daily note for {date_str}.",
            file_path=file_path,
            data={"date": date_str},
        )
