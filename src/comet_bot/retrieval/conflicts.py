"""Detect disagreements between active authoritative sources."""

from __future__ import annotations

from comet_bot.retrieval.models import SearchResult, SourceConflict

BREEZE_CLEANING_FILES = frozenset(
    {"11-product-care.md", "12-breeze-tumbler-product-card.md"}
)
BREEZE_TOPIC_TOKENS = frozenset({"breeze", "tumbler", "dishwasher", "cleaning", "wash"})


def _authoritative_files(results: list[SearchResult]) -> set[str]:
    return {
        result.chunk.source_file
        for result in results
        if result.chunk.metadata.get("is_authoritative")
    }


def _results_touch_topic(results: list[SearchResult], topic_tokens: set[str]) -> bool:
    for result in results:
        haystack = f"{result.chunk.heading} {result.chunk.text}".lower()
        if any(token in haystack for token in topic_tokens):
            return True
    return False


def detect_conflicts(results: list[SearchResult]) -> list[SourceConflict]:
    """Flag known corpus conflicts when both sides appear in authoritative results."""
    conflicts: list[SourceConflict] = []
    authoritative = _authoritative_files(results)

    if BREEZE_CLEANING_FILES.issubset(authoritative) and _results_touch_topic(
        results, set(BREEZE_TOPIC_TOKENS)
    ):
        conflicts.append(
            SourceConflict(
                topic="breeze_tumbler_cleaning",
                source_files=tuple(sorted(BREEZE_CLEANING_FILES)),
                description=(
                    "Active sources disagree on Breeze Tumbler cleaning: "
                    "product care says hand-wash the body, while the product card "
                    "says all components are dishwasher safe."
                ),
            )
        )

    return conflicts
