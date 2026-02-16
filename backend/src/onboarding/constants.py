"""Constants for the onboarding / demo data system."""

# Marker value stored in source_file column to identify demo rows.
DEMO_SOURCE_FILE = "__demo__"

# Key used in user_settings (Postgres) or settings.json (local) to persist onboarding state.
ONBOARDING_SETTINGS_KEY = "onboarding"

# Number of days of demo data to generate (relative to today).
DEMO_DAYS = 30

# Number of real daily notes before auto-graduating (clearing remaining demo data).
GRADUATION_THRESHOLD = 7
