"""Shared daily note template — fallback when vault template is missing."""

DAILY_NOTE_TEMPLATE = """\
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
"""


def render_daily_note() -> str:
    """Return the hardcoded fallback template.

    The vault template (Templates/daily.md) is preferred. This is only
    used when the vault template cannot be read.
    """
    return DAILY_NOTE_TEMPLATE
