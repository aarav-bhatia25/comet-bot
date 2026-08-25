"""Tests for retrieval ranking, conflict detection, and search."""

from __future__ import annotations

import pytest

from comet_bot.config import load_settings
from comet_bot.ingest import load_chunks
from comet_bot.retrieval import (
    DeterministicEmbedder,
    KnowledgeIndex,
    detect_conflicts,
    final_score,
    keyword_boost,
    metadata_boost,
)
from comet_bot.retrieval.models import SearchResult


def _chunk_by_file_and_heading(source_file: str, heading: str):
    for chunk in load_chunks():
        if chunk.source_file == source_file and chunk.heading == heading:
            return chunk
    raise AssertionError(f"Chunk not found: {source_file} > {heading}")


def _make_result(chunk, similarity: float, query: str) -> SearchResult:
    meta, keyword, score = final_score(similarity, chunk, query)
    return SearchResult(
        chunk=chunk,
        similarity_score=similarity,
        metadata_boost=meta,
        keyword_boost=keyword,
        final_score=score,
    )


def test_metadata_boost_prefers_authoritative_chunks() -> None:
    current = _chunk_by_file_and_heading("01-returns-policy-current.md", "Standard return window")
    legacy = _chunk_by_file_and_heading("02-returns-policy-legacy.md", "Return window")

    assert metadata_boost(current) > metadata_boost(legacy)


def test_keyword_boost_matches_numbers_in_query() -> None:
    chunk = _chunk_by_file_and_heading("01-returns-policy-current.md", "Standard return window")
    assert keyword_boost("30 calendar days return", chunk) > keyword_boost("shipping canada", chunk)


def test_rerank_demotes_superseded_when_similarity_is_equal() -> None:
    query = "return window"
    current = _chunk_by_file_and_heading("01-returns-policy-current.md", "Standard return window")
    legacy = _chunk_by_file_and_heading("02-returns-policy-legacy.md", "Return window")

    current_result = _make_result(current, similarity=0.80, query=query)
    legacy_result = _make_result(legacy, similarity=0.80, query=query)

    assert current_result.final_score > legacy_result.final_score


def test_detect_breeze_cleaning_conflict() -> None:
    care = _chunk_by_file_and_heading("11-product-care.md", "Breeze Tumbler")
    card = _chunk_by_file_and_heading("12-breeze-tumbler-product-card.md", "Cleaning")
    query = "Can I put the Breeze Tumbler in the dishwasher?"

    results = [
        _make_result(care, similarity=0.75, query=query),
        _make_result(card, similarity=0.74, query=query),
    ]
    conflicts = detect_conflicts(results)

    assert len(conflicts) == 1
    assert conflicts[0].topic == "breeze_tumbler_cleaning"
    assert set(conflicts[0].source_files) == {
        "11-product-care.md",
        "12-breeze-tumbler-product-card.md",
    }


def test_deterministic_index_prefers_current_returns_policy() -> None:
    index = KnowledgeIndex.build(embedder=DeterministicEmbedder())
    response = index.search(
        "How long does a regular customer have to return an unused backpack?",
        top_k=5,
    )

    top_files = [result.chunk.source_file for result in response.results]
    assert top_files[0] == "01-returns-policy-current.md"
    assert "02-returns-policy-legacy.md" not in top_files[:2]


def test_deterministic_index_finds_trailplus_return_window() -> None:
    index = KnowledgeIndex.build(embedder=DeterministicEmbedder())
    response = index.search(
        "TrailPlus membership return window when order was placed",
        top_k=5,
    )

    top_files = [result.chunk.source_file for result in response.results]
    assert "09-trailplus-membership.md" in top_files[:2]


@pytest.mark.integration
def test_openai_index_prefers_current_returns_policy() -> None:
    settings = load_settings()
    if not settings.openai_api_key or settings.openai_api_key == "your-openai-api-key-here":
        pytest.skip("OPENAI_API_KEY not configured")

    index = KnowledgeIndex.build()
    response = index.search(
        "How long does a regular customer have to return an unused backpack?",
        top_k=5,
    )

    top_files = [result.chunk.source_file for result in response.results]
    assert top_files[0] == "01-returns-policy-current.md"
    assert "02-returns-policy-legacy.md" not in top_files[:2]
