"""Run evaluation cases against a support agent."""

from __future__ import annotations

import uuid
from collections import defaultdict

from comet_bot.agent.protocol import SupportAgent
from comet_bot.eval.assertions import evaluate_expectations
from comet_bot.eval.loader import load_eval_cases
from comet_bot.eval.models import (
    CaseResult,
    CategorySummary,
    EvalCase,
    EvalReport,
)


def _preview(answer: str, limit: int = 120) -> str:
    compact = " ".join(answer.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def run_case(agent: SupportAgent, case: EvalCase) -> CaseResult:
    """Execute one eval case in a fresh conversation session."""
    messages = [{"role": message.role, "content": message.content} for message in case.messages]
    trace = agent.run(messages, session_id=str(uuid.uuid4()))
    assertions = evaluate_expectations(trace, case.expect)
    passed = all(result.passed for result in assertions)

    return CaseResult(
        case_id=case.id,
        category=case.category,
        passed=passed,
        assertions=tuple(assertions),
        answer_preview=_preview(trace.answer),
    )


def summarize_by_category(case_results: list[CaseResult]) -> list[CategorySummary]:
    totals: dict[str, list[bool]] = defaultdict(list)
    for result in case_results:
        totals[result.category].append(result.passed)

    return [
        CategorySummary(
            category=category,
            passed=sum(1 for passed in outcomes if passed),
            total=len(outcomes),
        )
        for category, outcomes in sorted(totals.items())
    ]


def run_evaluation(
    agent: SupportAgent,
    *,
    include_visible: bool = True,
    include_custom: bool = True,
    category: str | None = None,
) -> EvalReport:
    """Run all loaded cases and return a structured report."""
    cases = load_eval_cases(include_visible=include_visible, include_custom=include_custom)
    if category:
        cases = [case for case in cases if case.category == category]

    case_results = [run_case(agent, case) for case in cases]
    summaries = summarize_by_category(case_results)

    return EvalReport(
        case_results=tuple(case_results),
        category_summaries=tuple(summaries),
    )
