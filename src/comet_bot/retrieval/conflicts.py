"""Detect disagreements between active authoritative sources."""

from __future__ import annotations

from comet_bot.retrieval.models import SearchResult, SourceConflict

BREEZE_CLEANING_FILES = frozenset(
    {"11-product-care.md", "12-breeze-tumbler-product-card.md"}
)


def _authoritative_files(results: list[SearchResult]) -> set[str]:
    return {
        result.chunk.source_file
        for result in results
        if result.chunk.metadata.get("is_authoritative")
    }


def _query_touches_breeze_topic(query: str) -> bool:
    lower = query.lower()
    return any(token in lower for token in ("breeze", "tumbler", "dishwasher"))


def _breeze_specific_chunks_present(results: list[SearchResult]) -> bool:
    """True when retrieved chunks are about Breeze Tumbler care, not unrelated care sections."""
    breeze_files: set[str] = set()
    for result in results:
        if result.chunk.source_file not in BREEZE_CLEANING_FILES:
            continue
        heading = result.chunk.heading.lower()
        if "breeze" in heading or "tumbler" in heading or "cleaning" in heading:
            breeze_files.add(result.chunk.source_file)
    return breeze_files == BREEZE_CLEANING_FILES


def detect_conflicts(
    results: list[SearchResult],
    *,
    query: str = "",
) -> list[SourceConflict]:
    """Flag known corpus conflicts when both sides appear in authoritative results."""
    conflicts: list[SourceConflict] = []
    authoritative = _authoritative_files(results)

    if BREEZE_CLEANING_FILES.issubset(authoritative) and (
        _query_touches_breeze_topic(query) or _breeze_specific_chunks_present(results)
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
