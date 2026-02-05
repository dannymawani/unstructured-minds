# AI-Powered Suggestions

**Phase:** 5 - Extensibility
**Priority:** Low
**Status:** Not Started

## Description

Use AI to provide intelligent suggestions based on user's notes and habits.

## Tasks

- [ ] Daily reflection prompts
- [ ] Task suggestions based on patterns
- [ ] Anomaly detection (missed habits)
- [ ] Weekly insights generation
- [ ] Smart auto-complete in editor
- [ ] Related notes suggestions

## Acceptance Criteria

- Suggestions are contextually relevant
- Can dismiss/hide suggestions
- Insights generated weekly
- Auto-complete is helpful not intrusive
- Privacy-conscious (local processing when possible)

## Suggestion Types

1. **Prompts**: "You usually log exercise on Mondays"
2. **Insights**: "Your sleep improved 12% this month"
3. **Reminders**: "You haven't logged food today"
4. **Connections**: "This topic appears in 5 other notes"

## Implementation

```python
async def generate_insights(user_data: dict) -> list[Insight]:
    prompt = f"""
    Based on this user's data from the past week:
    {json.dumps(user_data)}

    Generate 3 actionable insights about:
    - Patterns and trends
    - Anomalies or missing data
    - Suggestions for improvement
    """
    return await claude.generate(prompt)
```

## UI

- Insights card on dashboard
- Inline suggestions in editor
- Daily digest option
