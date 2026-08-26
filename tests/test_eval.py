"""Tests for the evaluation loader, assertions, and runner."""

from __future__ import annotations

from comet_bot.agent.trace import AgentTrace, ToolCall
from comet_bot.eval import evaluate_expectations, load_eval_cases, run_case, run_evaluation
from comet_bot.eval.models import EvalCase, EvalMessage


class StaticAgent:
    def __init__(self, trace: AgentTrace) -> None:
        self.trace = trace

    def run(self, messages, *, session_id: str | None = None) -> AgentTrace:
        del messages, session_id
        return self.trace


def test_load_eval_cases_includes_visible_and_custom() -> None:
    cases = load_eval_cases()
    assert len(cases) == 20
    case_ids = {case.id for case in cases}
    assert "standard-return-window" in case_ids
    assert "custom-return-window-paraphrase" in case_ids


def test_must_include_assertion() -> None:
    trace = AgentTrace(answer="You have 30 calendar days from delivery.")
    results = evaluate_expectations(trace, {"must_include": ["30 calendar days", "delivery"]})
    assert all(result.passed for result in results)


def test_required_sources_assertion() -> None:
    trace = AgentTrace(
        answer="Returns are allowed within 30 calendar days.",
        source_files=["01-returns-policy-current.md", "07-warranty.md"],
    )
    results = evaluate_expectations(
        trace,
        {
            "required_sources": ["01-returns-policy-current.md"],
            "forbidden_sources_as_authority": ["02-returns-policy-legacy.md"],
        },
    )
    assert all(result.passed for result in results)


def test_tool_assertions_for_order_lookup() -> None:
    trace = AgentTrace(
        answer="Order ORD-1007 has shipped via UPS.",
        tool_calls=[ToolCall(name="order_lookup", arguments={"order_id": "ORD-1007"})],
    )
    results = evaluate_expectations(
        trace,
        {
            "tool": "order_lookup",
            "tool_arguments": {"order_id": "ORD-1007"},
        },
    )
    assert all(result.passed for result in results)


def test_handoff_assertion() -> None:
    trace = AgentTrace(answer="I recommend human support.", handoff_recommended=True)
    result = evaluate_expectations(trace, {"handoff": True})[0]
    assert result.passed


def test_run_case_with_static_agent() -> None:
    case = EvalCase(
        id="sample",
        category="retrieval",
        messages=(EvalMessage(role="user", content="return window"),),
        expect={"must_include": ["30 calendar days"], "tool": "not_called", "handoff": False},
    )
    trace = AgentTrace(answer="The return window is 30 calendar days from delivery.")
    result = run_case(StaticAgent(trace), case)
    assert result.passed


def test_run_evaluation_summary() -> None:
    case = EvalCase(
        id="one",
        category="retrieval",
        messages=(EvalMessage(role="user", content="hello"),),
        expect={"must_include": ["hello"]},
    )

    class SingleCaseAgent:
        def run(self, messages, *, session_id: str | None = None) -> AgentTrace:
            del messages, session_id
            return AgentTrace(answer="hello there")

    report = run_evaluation(
        SingleCaseAgent(),
        include_visible=False,
        include_custom=False,
    )
    # Empty when both disabled; run one case manually instead
    assert report.total == 0

    # Run with a fake agent on one crafted case through run_case instead
    trace = AgentTrace(answer="hello there")
    result = run_case(StaticAgent(trace), case)
    assert result.passed
