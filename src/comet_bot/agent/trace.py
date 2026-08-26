"""Structured record of one agent run for evaluation and debugging."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolCall:
    """One tool invocation made during an agent turn."""

    name: str
    arguments: dict[str, Any]


@dataclass
class AgentTrace:
    """Everything eval and observability need from a single agent run."""

    answer: str
    sources: list[str] = field(default_factory=list)
    source_files: list[str] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)
    handoff_recommended: bool = False
    messages: list[dict[str, str]] = field(default_factory=list)
    retrieved_chunks: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def primary_source_files(self) -> list[str]:
        """Unique source files cited or retrieved, in first-seen order."""
        seen: set[str] = set()
        ordered: list[str] = []
        for source_file in self.source_files:
            if source_file not in seen:
                seen.add(source_file)
                ordered.append(source_file)
        return ordered

    def tool_names(self) -> list[str]:
        return [call.name for call in self.tool_calls]
