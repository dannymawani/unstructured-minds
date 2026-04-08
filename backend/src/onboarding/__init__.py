"""Onboarding module: demo data generation and lifecycle management."""

from .constants import DEMO_SOURCE_FILE, ONBOARDING_SETTINGS_KEY
from .demo_data import generate_demo_data
from .lifecycle import check_graduation, cleanup_demo_for_date, clear_all_demo_data
from .seed import seed_demo_data

__all__ = [
    "DEMO_SOURCE_FILE",
    "ONBOARDING_SETTINGS_KEY",
    "generate_demo_data",
    "seed_demo_data",
    "cleanup_demo_for_date",
    "clear_all_demo_data",
    "check_graduation",
]
