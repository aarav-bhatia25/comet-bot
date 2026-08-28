"""Structured debug logging for agent runs."""

from __future__ import annotations

import json
import sys
from typing import Any

from comet_bot.config import load_settings


def log_debug_event(event: str, payload: dict[str, Any]) -> None:
    """Print a structured debug record when DEBUG is enabled."""
    settings = load_settings()
    if not settings.debug:
        return

    record = {"event": event, **payload}
    print(json.dumps(record, indent=2, default=str), file=sys.stderr)
