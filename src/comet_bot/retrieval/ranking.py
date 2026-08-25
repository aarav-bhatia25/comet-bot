"""Score adjustments for retrieval ranking."""

from __future__ import annotations

import re

from comet_bot.ingest.models import Chunk

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

# Tunable weights — small corpus, so modest boosts are enough.
AUTHORITATIVE_BOOST = 0.15
SUPERSEDED_PENALTY = 0.20
INTERNAL_PENALTY = 0.25
KEYWORD_WEIGHT = 0.10


def tokenize(text: str) -> set[str]:
    """Lowercase alphanumeric tokens, including numbers like 30 or 45."""
    return set(_TOKEN_PATTERN.findall(text.lower()))


def metadata_boost(chunk: Chunk) -> float:
    """Boost or penalize chunks based on derived precedence flags."""
    metadata = chunk.metadata
    boost = 0.0

    if metadata.get("is_authoritative"):
        boost += AUTHORITATIVE_BOOST
    if metadata.get("is_superseded"):
        boost -= SUPERSEDED_PENALTY
    if metadata.get("is_internal"):
        boost -= INTERNAL_PENALTY

    return boost


def keyword_boost(query: str, chunk: Chunk) -> float:
    """Light overlap score to help short policy docs with numbers and jargon."""
    query_tokens = tokenize(query)
    if not query_tokens:
        return 0.0

    chunk_tokens = tokenize(chunk.text)
    overlap = len(query_tokens & chunk_tokens) / len(query_tokens)
    return overlap


def final_score(similarity: float, chunk: Chunk, query: str) -> tuple[float, float, float]:
    """Return (metadata_boost, keyword_boost, final_score)."""
    meta = metadata_boost(chunk)
    keyword = keyword_boost(query, chunk)
    total = similarity + meta + (keyword * KEYWORD_WEIGHT)
    return meta, keyword, total
