"""Generate demo daily notes as markdown files.

Creates realistic daily notes in the vault directory for the past N days,
showing what the app looks like with real content.
"""

import random
from datetime import date, timedelta
from pathlib import Path

WORKOUT_TEMPLATES = [
    ("Strength — Upper", [
        "- Bench Press: 4x8 @ 80kg",
        "- Overhead Press: 3x10 @ 45kg",
        "- Barbell Row: 4x8 @ 70kg",
        "- Pull-ups: 3x12 bodyweight",
        "- Dumbbell Curl: 3x12 @ 14kg",
    ]),
    ("Strength — Legs", [
        "- Squat: 4x6 @ 120kg",
        "- Romanian Deadlift: 3x10 @ 100kg",
        "- Leg Press: 4x12 @ 180kg",
        "- Calf Raises: 3x15 @ 60kg",
    ]),
    ("Strength — Pull", [
        "- Deadlift: 4x5 @ 140kg",
        "- Pull-ups: 4x10 bodyweight",
        "- Barbell Row: 3x8 @ 75kg",
        "- Face Pulls: 3x15 @ 20kg",
    ]),
    ("BJJ", [
        "- BJJ: 90 minutes rolling and drilling",
        "- Focused on guard retention and sweeps",
    ]),
    ("Cardio", [
        "- Cycling: 25km in 55 minutes",
        "- Heart rate avg 145 bpm",
    ]),
]

WORK_ITEMS = [
    "Review pull requests",
    "Sprint planning meeting",
    "Fix authentication bug",
    "Write API documentation",
    "Deploy staging environment",
    "Code review for new feature",
    "Database migration planning",
    "1:1 with team lead",
    "Refactor extraction pipeline",
    "Update dependencies",
]

PERSONAL_ITEMS = [
    "Grocery shopping",
    "Call dentist",
    "Read 30 pages",
    "Laundry",
    "Cook meal prep for the week",
    "Pay electricity bill",
    "Clean apartment",
    "Call parents",
    "Order new running shoes",
    "Meditation — 15 minutes",
]

ADHOC_NOTES = [
    "Had a great conversation about startup ideas with Alex",
    "New coffee place on 5th street is really good",
    "Idea: build a CLI tool for note search",
    "Remember to check the Rust conference talk schedule",
    "Feeling motivated after the workout — PRs are coming",
    "Need to look into better sleep hygiene",
    "Podcast recommendation from Tom: Huberman Lab on sleep",
]


def generate_daily_note(d: date) -> str:
    """Generate a realistic daily note for a given date."""
    weekday = d.strftime("%A")
    date_str = d.strftime("%B %-d, %Y")
    is_rest = random.random() < 0.2  # 20% chance rest day

    # Workout
    if is_rest:
        workout_type = "Rest"
        workout_lines = ["- Rest day"]
    else:
        workout_type, workout_lines = random.choice(WORKOUT_TEMPLATES)

    sleep = round(random.uniform(6.0, 9.0), 1)
    energy = random.randint(5, 10)
    mood = random.randint(5, 10)

    work = random.sample(WORK_ITEMS, k=random.randint(2, 4))
    personal = random.sample(PERSONAL_ITEMS, k=random.randint(1, 3))
    focus = random.sample(work + personal, k=min(3, len(work) + len(personal)))
    adhoc = random.sample(ADHOC_NOTES, k=random.randint(0, 2))

    lines = [
        f"# {weekday} {date_str}",
        "",
        "## 🏋️ Training & Health",
        "",
        "### Workout",
        f"- **Type**: {workout_type}",
    ]
    if not is_rest:
        lines.append(f"- **Focus**: {workout_type.split(' — ')[-1] if ' — ' in workout_type else workout_type}")
    lines.extend(workout_lines)
    lines.extend([
        "",
        "### Energy & Recovery",
        f"- Sleep: {sleep}h ({int(sleep + 0.5)}/10)",
        f"- Energy Level: {energy}/10",
        f"- Mood: {mood}/10",
        "- Nutrition: ",
        "",
        "## 🎯 Today's Focus",
        "",
    ])
    for item in focus:
        done = random.random() < 0.6
        lines.append(f"- [{'x' if done else ' '}] {item}")

    lines.extend(["", "## 💼 Work", ""])
    for item in work:
        done = random.random() < 0.5
        lines.append(f"- [{'x' if done else ' '}] {item}")

    lines.extend(["", "## 🤷🏽 Personal", ""])
    for item in personal:
        done = random.random() < 0.4
        lines.append(f"- [{'x' if done else ' '}] {item}")

    lines.extend(["", "## 📝 Adhoc Notes", ""])
    if adhoc:
        for note in adhoc:
            lines.append(f"- {note}")
    else:
        lines.append("- ")

    lines.append("")
    return "\n".join(lines)


def seed_vault(vault_path: Path, days: int = 14) -> int:
    """Generate demo daily notes in the vault.

    Args:
        vault_path: Path to the vault directory
        days: Number of days of notes to generate

    Returns:
        Number of notes created
    """
    vault_path.mkdir(parents=True, exist_ok=True)
    count = 0

    for i in range(days):
        d = date.today() - timedelta(days=days - 1 - i)
        filename = f"{d.isoformat()}.md"
        filepath = vault_path / filename

        # Don't overwrite existing notes
        if filepath.exists():
            continue

        filepath.write_text(generate_daily_note(d))
        count += 1

    return count


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Seed demo notes")
    parser.add_argument("--vault-path", default="./vault", help="Path to vault directory")
    parser.add_argument("--days", type=int, default=14, help="Number of days of notes")
    args = parser.parse_args()

    count = seed_vault(Path(args.vault_path), args.days)
    print(f"Created {count} demo notes in {args.vault_path}")
