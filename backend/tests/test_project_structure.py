"""Test project structure exists."""

from pathlib import Path

# Get the backend directory (parent of tests directory)
BACKEND_DIR = Path(__file__).parent.parent


def test_src_directory_exists():
    """Verify src directory exists."""
    assert (BACKEND_DIR / "src").exists()


def test_required_modules_exist():
    """Verify all required modules exist."""
    modules = ["claude", "db", "api", "storage", "watcher"]
    for mod in modules:
        assert (BACKEND_DIR / "src" / mod).exists(), f"Module {mod} not found"
        assert (BACKEND_DIR / "src" / mod / "__init__.py").exists(), f"Module {mod} missing __init__.py"


def test_config_exists():
    """Verify config module exists."""
    assert (BACKEND_DIR / "src" / "config.py").exists()


def test_pyproject_exists():
    """Verify pyproject.toml exists."""
    assert (BACKEND_DIR / "pyproject.toml").exists()
