"""Tests for the web API."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi.testclient import TestClient

from comet_bot.agent import SessionStore
from comet_bot.agent.trace import AgentTrace, ToolCall
from comet_bot.web import create_app


@dataclass
class FakeAgent:
    def run(self, messages, *, session_id=None):
        del session_id
        return AgentTrace(
            answer="Your order has **shipped** with UPS.",
            sources=["01-returns-policy-current.md > Standard return window"],
            source_files=["01-returns-policy-current.md"],
            tool_calls=[ToolCall(name="order_lookup", arguments={"order_id": "ORD-1007"})],
            handoff_recommended=False,
            messages=list(messages),
        )


def test_index_returns_html() -> None:
    client = TestClient(create_app(agent=FakeAgent(), sessions=SessionStore()))
    response = client.get("/")
    assert response.status_code == 200
    assert "Aster &amp; Row" in response.text


def test_create_session_returns_id() -> None:
    client = TestClient(create_app(agent=FakeAgent(), sessions=SessionStore()))
    response = client.post("/api/sessions")
    assert response.status_code == 200
    assert "session_id" in response.json()


def test_chat_returns_agent_response() -> None:
    sessions = SessionStore()
    client = TestClient(create_app(agent=FakeAgent(), sessions=sessions))

    session_id = client.post("/api/sessions").json()["session_id"]
    response = client.post(
        "/api/chat",
        json={"session_id": session_id, "message": "Where is ORD-1007?"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"] == session_id
    assert "shipped" in payload["answer"]
    assert payload["source_files"] == ["01-returns-policy-current.md"]
    assert payload["tool_calls"][0]["name"] == "order_lookup"

    session = sessions.get(session_id)
    assert len(session.messages) == 2
    assert session.messages[0]["role"] == "user"
    assert session.messages[1]["role"] == "assistant"


def test_chat_rejects_empty_message() -> None:
    client = TestClient(create_app(agent=FakeAgent(), sessions=SessionStore()))
    response = client.post("/api/chat", json={"message": "   "})
    assert response.status_code == 422
