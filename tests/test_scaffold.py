"""Smoke tests for Step 0 — verify paths and package imports work."""

from pathlib import Path

from comet_bot import __version__
from comet_bot.config import (
    KNOWLEDGE_BASE_DIR,
    ORDERS_FILE,
    REPO_ROOT,
    VISIBLE_CASES_FILE,
    verify_data_paths,
)


def test_package_version() -> None:
    assert __version__ == "0.1.0"


def test_repo_root_exists() -> None:
    assert REPO_ROOT.is_dir()
    assert (REPO_ROOT / "README.md").is_file()


def test_assignment_data_paths_exist() -> None:
    assert verify_data_paths() == []
    assert KNOWLEDGE_BASE_DIR.is_dir()
    assert len(list(KNOWLEDGE_BASE_DIR.glob("*.md"))) == 14
    assert ORDERS_FILE.is_file()
    assert VISIBLE_CASES_FILE.is_file()


def test_knowledge_base_files_are_markdown() -> None:
    for path in KNOWLEDGE_BASE_DIR.glob("*.md"):
        assert path.suffix == ".md"
        assert path.stat().st_size > 0
