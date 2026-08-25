"""Data models for retrieval results."""

from __future__ import annotations

from dataclasses import dataclass

from comet_bot.ingest.models import Chunk


@dataclass(frozen=True)
class SearchResult:
    """One ranked chunk returned from knowledge-base search."""

    chunk: Chunk
    similarity_score: float
    metadata_boost: float
    keyword_boost: float
    final_score: float


@dataclass(frozen=True)
class SourceConflict:
    """A known or detected disagreement between active authoritative sources."""

    topic: str
    source_files: tuple[str, ...]
    description: str


@dataclass(frozen=True)
class RetrievalResponse:
    """Full output from a knowledge-base search."""

    query: str
    results: tuple[SearchResult, ...]
    conflicts: tuple[SourceConflict, ...]
