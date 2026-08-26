"""Central configuration: repo paths, environment variables, and defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Repo root is two levels above this file: src/comet_bot/config.py -> repo root
REPO_ROOT = Path(__file__).resolve().parents[2]

# Supplied assignment data (read-only — we do not modify these)
KNOWLEDGE_BASE_DIR = REPO_ROOT / "knowledge-base"
DATA_DIR = REPO_ROOT / "data"
ORDERS_FILE = DATA_DIR / "orders.json"
ORDERS_DATA_DICTIONARY = DATA_DIR / "orders-data-dictionary.md"
EVALUATION_DIR = REPO_ROOT / "evaluation"
VISIBLE_CASES_FILE = EVALUATION_DIR / "visible-cases.json"
CUSTOM_CASES_FILE = EVALUATION_DIR / "custom-cases.json"

# Sensible defaults; override via .env if needed
DEFAULT_CHAT_MODEL = "gpt-4o-mini"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


@dataclass(frozen=True)
class Settings:
    """Runtime settings loaded from environment variables."""

    openai_api_key: str | None
    chat_model: str
    embedding_model: str
    debug: bool


def load_settings() -> Settings:
    """Load .env from repo root and return application settings."""
    load_dotenv(REPO_ROOT / ".env")

    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        chat_model=os.getenv("OPENAI_CHAT_MODEL", DEFAULT_CHAT_MODEL),
        embedding_model=os.getenv("OPENAI_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL),
        debug=os.getenv("DEBUG", "false").lower() in {"1", "true", "yes"},
    )


def verify_data_paths() -> list[str]:
    """Return a list of human-readable errors if expected paths are missing."""
    errors: list[str] = []

    if not KNOWLEDGE_BASE_DIR.is_dir():
        errors.append(f"Knowledge base directory not found: {KNOWLEDGE_BASE_DIR}")

    if not ORDERS_FILE.is_file():
        errors.append(f"Orders file not found: {ORDERS_FILE}")

    if not VISIBLE_CASES_FILE.is_file():
        errors.append(f"Evaluation cases file not found: {VISIBLE_CASES_FILE}")

    if not CUSTOM_CASES_FILE.is_file():
        errors.append(f"Custom evaluation cases file not found: {CUSTOM_CASES_FILE}")

    return errors
