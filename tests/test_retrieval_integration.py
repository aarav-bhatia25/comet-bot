"""Retrieval integration checks."""

from __future__ import annotations

import pytest

from comet_bot.config import load_settings
from comet_bot.retrieval import KnowledgeIndex


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
