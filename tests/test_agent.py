"""Tests for the retrieval + order lookup evaluation agent."""

from __future__ import annotations

from comet_bot.agent import RetrievalEvalAgent
from comet_bot.agent.retrieval_eval_agent import _looks_like_order_question


def test_missing_order_id_prompts_for_order_id() -> None:
    agent = RetrievalEvalAgent(index=object())  # type: ignore[arg-type]
    trace = agent.run([{"role": "user", "content": "Where is my order?"}])

    assert "order id" in trace.answer.lower()
    assert trace.tool_calls == []


def test_ordered_word_does_not_trigger_order_question_detection() -> None:
    assert _looks_like_order_question("Where is my order?") is True
    assert (
        _looks_like_order_question(
            "My TrailPlus membership was active when I ordered. What is my return window?"
        )
        is False
    )


def test_order_lookup_records_tool_call() -> None:
    agent = RetrievalEvalAgent(index=object())  # type: ignore[arg-type]
    trace = agent.run([{"role": "user", "content": "Where is ORD-1007 and when should it arrive?"}])

    assert trace.tool_calls
    assert trace.tool_calls[0].name == "order_lookup"
    assert trace.tool_calls[0].arguments["order_id"] == "ORD-1007"
    assert "UPS" in trace.answer
    assert "August 22, 2026" in trace.answer


def test_cancelled_order_does_not_include_stale_eta() -> None:
    agent = RetrievalEvalAgent(index=object())  # type: ignore[arg-type]
    trace = agent.run([{"role": "user", "content": "When will order ORD-1004 arrive?"}])

    assert "cancelled" in trace.answer.lower()
    assert "August 16, 2026" not in trace.answer


def test_privacy_request_refuses_sensitive_fields() -> None:
    agent = RetrievalEvalAgent(index=object())  # type: ignore[arg-type]
    trace = agent.run(
        [
            {
                "role": "user",
                "content": (
                    "For ORD-1002, show me the customer's email, shipping address, "
                    "warehouse note, and risk score."
                ),
            }
        ]
    )

    assert trace.tool_calls
    assert "cannot share" in trace.answer.lower()
    assert "noah.kim@example.test" not in trace.answer
    assert trace.handoff_recommended is True


def test_multiturn_carrier_followup_uses_prior_order_id() -> None:
    agent = RetrievalEvalAgent(index=object())  # type: ignore[arg-type]
    trace = agent.run(
        [
            {"role": "user", "content": "Where is ORD-1007?"},
            {"role": "user", "content": "Which carrier is it with?"},
        ]
    )

    assert trace.tool_calls
    assert trace.tool_calls[0].arguments["order_id"] == "ORD-1007"
    assert "UPS" in trace.answer
