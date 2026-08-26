"""Agent protocol for evaluation and interfaces."""

from __future__ import annotations

from typing import Protocol

from comet_bot.agent.trace import AgentTrace


class SupportAgent(Protocol):
    """Any agent implementation the evaluation runner can exercise."""

    def run(self, messages: list[dict[str, str]], *, session_id: str | None = None) -> AgentTrace:
        """Run the full message list in one conversation session."""
