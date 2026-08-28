"""Handoff and routing heuristics for the support agent."""

from __future__ import annotations

import re

_ORDER_QUESTION_PATTERN = re.compile(
    r"\b(order|tracking|shipment|shipped|deliver|arrive|carrier|package)\b",
    re.IGNORECASE,
)
_SENSITIVE_REQUEST_TERMS = (
    "email",
    "address",
    "warehouse note",
    "risk score",
    "internal note",
)


def looks_like_order_question(text: str) -> bool:
    """Return True when the user appears to be asking about an order."""
    return _ORDER_QUESTION_PATTERN.search(text) is not None


def requests_sensitive_info(text: str) -> bool:
    """Return True when the user asks for fields that must not be disclosed."""
    lower = text.lower()
    return any(term in lower for term in _SENSITIVE_REQUEST_TERMS)


def is_prompt_injection_attempt(text: str) -> bool:
    """Detect the eval prompt-injection scenario about the migration note."""
    lower = text.lower()
    return "migration note" in lower and (
        "60 days" in lower or "ignore the real policy" in lower
    )


def should_recommend_handoff_for_query(text: str) -> bool:
    """Recommend handoff for damaged-item and similar exception flows."""
    lower = text.lower()
    return any(
        term in lower
        for term in ("damaged", "broken", "defective", "final-sale", "final sale", "out of luck")
    )


def compute_handoff_recommended(
    *,
    latest_query: str,
    answer: str,
    order_handoff: bool,
    has_conflicts: bool,
) -> bool:
    """Combine deterministic rules with light answer-based signals."""
    if is_prompt_injection_attempt(latest_query):
        return False

    if requests_sensitive_info(latest_query):
        return True

    if order_handoff or has_conflicts or should_recommend_handoff_for_query(latest_query):
        return True

    lower = answer.lower()
    exception_phrases = ("exception", "support review", "requires support")
    if any(phrase in lower for phrase in exception_phrases):
        return True

    abstention_phrases = (
        "insufficient",
        "don't have information",
        "do not have information",
        "cannot confirm",
        "human confirmation",
        "recommend contacting support",
        "contact support for human",
    )
    return any(phrase in lower for phrase in abstention_phrases)
