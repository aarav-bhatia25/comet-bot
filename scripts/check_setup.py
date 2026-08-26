#!/usr/bin/env python3
"""Quick setup check — run after installing dependencies."""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running before `pip install -e .` by adding src/ to the path.
SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

from comet_bot import __version__  # noqa: E402
from comet_bot.config import (  # noqa: E402
    CUSTOM_CASES_FILE,
    KNOWLEDGE_BASE_DIR,
    ORDERS_FILE,
    VISIBLE_CASES_FILE,
    load_settings,
    verify_data_paths,
)


def main() -> int:
    print(f"comet-bot v{__version__} — setup check\n")

    errors = verify_data_paths()
    if errors:
        print("Data path errors:")
        for error in errors:
            print(f"  - {error}")
        return 1

    kb_count = len(list(KNOWLEDGE_BASE_DIR.glob("*.md")))
    print(f"Knowledge base: {kb_count} markdown files in {KNOWLEDGE_BASE_DIR}")
    print(f"Orders data:      {ORDERS_FILE}")
    print(f"Visible cases:    {VISIBLE_CASES_FILE}")
    print(f"Custom cases:     {CUSTOM_CASES_FILE}")

    settings = load_settings()
    if settings.openai_api_key:
        print("\nOPENAI_API_KEY: set")
    else:
        print("\nOPENAI_API_KEY: not set (copy .env.example to .env)")

    print(f"Chat model:       {settings.chat_model}")
    print(f"Embedding model:  {settings.embedding_model}")
    print("\nSetup looks good. Next step: build the full support agent in src/comet_bot/agent/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
