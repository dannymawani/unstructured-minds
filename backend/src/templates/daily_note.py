"""Shared daily note template — single source of truth.

Matches the Obsidian template at:
  /Users/dmh/Code/obsedian/secondbrain/Templates/Daily-Note-Template.md
"""

from datetime import datetime, timedelta

DAILY_NOTE_TEMPLATE = """\
---
date: {date}
type: daily-note
tags:
  - daily
  - journal
---

## 📝 Adhoc Notes
-

## 🎯 Today's Focus

- [ ]

- [ ]

## 💼 Work


## 🤷🏽 Personal


## 🏋️ Training & Health
### Workout
- **Type**:
- **Focus**:

### Energy & Recovery
- Sleep:
- Energy Level:
- Mood:
- Nutrition:

---
**Previous**: [[{prev_date}]] | **Next**: [[{next_date}]]
"""


def render_daily_note(date_str: str) -> str:
    """Render a daily note from the shared template.

    Args:
        date_str: Date in YYYY-MM-DD format.

    Returns:
        Fully rendered markdown string.
    """
    date = datetime.strptime(date_str, "%Y-%m-%d")
    prev_date = (date - timedelta(days=1)).strftime("%Y-%m-%d")
    next_date = (date + timedelta(days=1)).strftime("%Y-%m-%d")

    return DAILY_NOTE_TEMPLATE.format(
        date=date_str,
        prev_date=prev_date,
        next_date=next_date,
    )
