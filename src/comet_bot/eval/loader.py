"""Load visible and custom evaluation cases."""

from __future__ import annotations

import json
from pathlib import Path

from comet_bot.config import CUSTOM_CASES_FILE, VISIBLE_CASES_FILE
from comet_bot.eval.models import EvalCase, EvalMessage


def _parse_case(raw: dict) -> EvalCase:
    messages = tuple(
        EvalMessage(role=message["role"], content=message["content"])
        for message in raw["messages"]
    )
    return EvalCase(
        id=raw["id"],
        category=raw["category"],
        messages=messages,
        expect=dict(raw["expect"]),
    )


def _load_case_file(path: Path) -> list[EvalCase]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [_parse_case(case) for case in payload["cases"]]


def load_eval_cases(
    *,
    include_visible: bool = True,
    include_custom: bool = True,
) -> list[EvalCase]:
    """Load all evaluation cases from disk."""
    cases: list[EvalCase] = []

    if include_visible:
        cases.extend(_load_case_file(VISIBLE_CASES_FILE))
    if include_custom:
        cases.extend(_load_case_file(CUSTOM_CASES_FILE))

    return cases
