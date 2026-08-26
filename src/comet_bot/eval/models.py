"""Evaluation data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class EvalMessage:
    role: str
    content: str


@dataclass(frozen=True)
class EvalCase:
    id: str
    category: str
    messages: tuple[EvalMessage, ...]
    expect: dict[str, Any]


@dataclass(frozen=True)
class AssertionResult:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    category: str
    passed: bool
    assertions: tuple[AssertionResult, ...]
    answer_preview: str = ""


@dataclass(frozen=True)
class CategorySummary:
    category: str
    passed: int
    total: int


@dataclass(frozen=True)
class EvalReport:
    case_results: tuple[CaseResult, ...]
    category_summaries: tuple[CategorySummary, ...]

    @property
    def passed(self) -> int:
        return sum(1 for result in self.case_results if result.passed)

    @property
    def total(self) -> int:
        return len(self.case_results)

    @property
    def all_passed(self) -> bool:
        return self.passed == self.total
