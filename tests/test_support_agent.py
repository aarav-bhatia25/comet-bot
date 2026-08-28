"""Tests for the LLM support agent with a mocked OpenAI client."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from comet_bot.agent.support_agent import SupportAgent
from comet_bot.retrieval import DeterministicEmbedder, KnowledgeIndex


@dataclass
class FakeMessage:
    content: str


@dataclass
class FakeChoice:
    message: FakeMessage


@dataclass
class FakeCompletion:
    choices: list[FakeChoice]


class FakeCompletions:
    def __init__(self, answer: str) -> None:
        self.answer = answer

    def create(self, **kwargs):
        del kwargs
        return FakeCompletion(choices=[FakeChoice(message=FakeMessage(content=self.answer))])


class FakeClient:
    def __init__(self, answer: str) -> None:
        self.chat = SimpleNamespace(completions=FakeCompletions(answer))


@pytest.fixture
def deterministic_agent() -> SupportAgent:
    index = KnowledgeIndex.build(embedder=DeterministicEmbedder())
    client = FakeClient(
        "You may return eligible items within 30 calendar days of delivery. "
        "[01-returns-policy-current.md > Standard return window]"
    )
    return SupportAgent(
        index=index,
        settings=SimpleNamespace(
            openai_api_key="test-key",
            chat_model="gpt-4o-mini",
            embedding_model="text-embedding-3-small",
            debug=False,
        ),
        client=client,  # type: ignore[arg-type]
    )


def test_support_agent_returns_llm_answer_with_sources(deterministic_agent: SupportAgent) -> None:
    trace = deterministic_agent.run(
        [{"role": "user", "content": "How long does a regular customer have to return a backpack?"}]
    )

    assert "30 calendar days" in trace.answer
    assert "01-returns-policy-current.md" in trace.primary_source_files
    assert trace.tool_calls == []


def test_support_agent_calls_order_lookup_when_id_present() -> None:
    index = KnowledgeIndex.build(embedder=DeterministicEmbedder())
    client = FakeClient(
        "Your order ORD-1007 has shipped with UPS and is estimated to arrive on August 22, 2026."
    )
    agent = SupportAgent(
        index=index,
        settings=SimpleNamespace(
            openai_api_key="test-key",
            chat_model="gpt-4o-mini",
            embedding_model="text-embedding-3-small",
            debug=False,
        ),
        client=client,  # type: ignore[arg-type]
    )

    trace = agent.run(
        [{"role": "user", "content": "Where is ORD-1007 and when should it arrive?"}]
    )

    assert trace.tool_calls
    assert trace.tool_calls[0].name == "order_lookup"
    assert trace.tool_calls[0].arguments["order_id"] == "ORD-1007"


def test_support_agent_asks_for_order_id_without_lookup() -> None:
    index = KnowledgeIndex.build(embedder=DeterministicEmbedder())
    client = FakeClient("Please share your order ID so I can look it up.")
    agent = SupportAgent(
        index=index,
        settings=SimpleNamespace(
            openai_api_key="test-key",
            chat_model="gpt-4o-mini",
            embedding_model="text-embedding-3-small",
            debug=False,
        ),
        client=client,  # type: ignore[arg-type]
    )

    trace = agent.run([{"role": "user", "content": "Where is my order?"}])

    assert trace.tool_calls == []
    assert "order id" in trace.answer.lower()


@pytest.mark.integration
def test_support_agent_live_return_window() -> None:
    from comet_bot.config import load_settings

    settings = load_settings()
    if not settings.openai_api_key or settings.openai_api_key == "your-openai-api-key-here":
        pytest.skip("OPENAI_API_KEY not configured")

    agent = SupportAgent()
    trace = agent.run(
        [{"role": "user", "content": "How long does a regular customer have to return a backpack?"}]
    )

    assert "30" in trace.answer
    assert "01-returns-policy-current.md" in trace.primary_source_files
