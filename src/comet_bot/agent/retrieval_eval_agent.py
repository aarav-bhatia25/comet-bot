"""Temporary retrieval-only agent for early evaluation before full Step 5 agent."""

from __future__ import annotations

import re
import uuid

from comet_bot.agent.trace import AgentTrace
from comet_bot.retrieval import KnowledgeIndex

_ORDER_ID_PATTERN = re.compile(r"\bORD-\d{4}\b", re.IGNORECASE)


class RetrievalEvalAgent:
    """Uses retrieval to answer policy questions; does not call order tools yet."""

    def __init__(self, index: KnowledgeIndex | None = None) -> None:
        self.index = index or KnowledgeIndex.build()

    def run(
        self,
        messages: list[dict[str, str]],
        *,
        session_id: str | None = None,
    ) -> AgentTrace:
        del session_id  # single-session runner manages ids externally

        user_messages = [message["content"] for message in messages if message["role"] == "user"]
        latest_query = user_messages[-1] if user_messages else ""
        combined_query = "\n".join(user_messages)

        if _ORDER_ID_PATTERN.search(combined_query):
            return AgentTrace(
                answer=(
                    "I can look up orders, but the order lookup tool is not wired into this "
                    "evaluation agent yet."
                ),
                messages=list(messages),
                handoff_recommended=False,
                errors=["order_lookup_not_implemented"],
            )

        response = self.index.search(combined_query, top_k=5)
        if not response.results:
            return AgentTrace(
                answer="I do not have enough information in the knowledge base to answer that.",
                messages=list(messages),
                handoff_recommended=True,
            )

        top_chunks = [result.chunk for result in response.results]
        authoritative_chunks = [
            chunk for chunk in top_chunks if chunk.metadata.get("is_authoritative")
        ]
        chunks_for_answer = authoritative_chunks[:2] or top_chunks[:1]
        answer_parts = [chunk.text for chunk in chunks_for_answer]
        answer = "\n\n".join(answer_parts)

        citation_chunks = authoritative_chunks[:3] or top_chunks[:3]
        sources = [f"{chunk.source_file} > {chunk.heading}" for chunk in citation_chunks]
        source_files = [chunk.source_file for chunk in citation_chunks]
        conflicts = [conflict.topic for conflict in response.conflicts]

        return AgentTrace(
            answer=answer,
            sources=sources,
            source_files=source_files,
            handoff_recommended=bool(conflicts),
            messages=list(messages),
            retrieved_chunks=[chunk.id for chunk in citation_chunks],
            conflicts=conflicts,
        )
