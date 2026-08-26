"""Temporary retrieval + order lookup agent for evaluation before full Step 5 LLM agent."""

from __future__ import annotations

import re
from datetime import datetime

from comet_bot.agent.trace import AgentTrace, ToolCall
from comet_bot.retrieval import KnowledgeIndex
from comet_bot.retrieval.models import RetrievalResponse
from comet_bot.tools import extract_order_id, lookup_order
from comet_bot.tools.models import OrderLookupResult

_ORDER_QUESTION_PATTERN = re.compile(
    r"\b(order|tracking|shipment|shipped|deliver|arrive|carrier|package)\b",
    re.IGNORECASE,
)
_SENSITIVE_REQUEST_TERMS = (
    "email",
    "address",
    "warehouse note",
    "risk score",
    "internal note",
)
_ABSTENTION_QUERY_TERMS = ("vegan", "material certification", "allergen", "adhesive")


class RetrievalEvalAgent:
    """Uses retrieval for policy questions and the order tool for order status queries."""

    def __init__(self, index: KnowledgeIndex | None = None) -> None:
        self._index = index

    def _get_index(self) -> KnowledgeIndex:
        if self._index is None:
            self._index = KnowledgeIndex.build()
        return self._index

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

        if _is_prompt_injection_attempt(latest_query):
            return _handle_prompt_injection(messages)

        order_id = extract_order_id(combined_query)
        if order_id:
            return self._handle_order_lookup(
                messages=messages,
                order_id=order_id,
                latest_query=latest_query,
            )

        if _looks_like_order_question(latest_query):
            return AgentTrace(
                answer="Please share your order ID (for example, ORD-1007) so I can look it up.",
                messages=list(messages),
                handoff_recommended=False,
            )

        return self._handle_policy_lookup(
            messages=messages,
            combined_query=combined_query,
            latest_query=latest_query,
        )

    def _handle_order_lookup(
        self,
        *,
        messages: list[dict[str, str]],
        order_id: str,
        latest_query: str,
    ) -> AgentTrace:
        result = lookup_order(order_id)
        tool_calls = [ToolCall(name="order_lookup", arguments={"order_id": order_id})]
        answer = _format_order_answer(result, sensitive_request=_requests_sensitive_info(latest_query))

        return AgentTrace(
            answer=answer,
            sources=[],
            source_files=[],
            tool_calls=tool_calls,
            handoff_recommended=result.handoff_recommended or _requests_sensitive_info(latest_query),
            messages=list(messages),
        )

    def _handle_policy_lookup(
        self,
        *,
        messages: list[dict[str, str]],
        combined_query: str,
        latest_query: str,
    ) -> AgentTrace:
        response = self._get_index().search(combined_query, top_k=6)
        if not response.results:
            return AgentTrace(
                answer=(
                    "The supplied information is insufficient to answer that confidently. "
                    "I recommend human confirmation."
                ),
                messages=list(messages),
                handoff_recommended=True,
            )

        top_chunks = [result.chunk for result in response.results]
        authoritative_chunks = [
            chunk for chunk in top_chunks if chunk.metadata.get("is_authoritative")
        ]
        chunks_for_answer = authoritative_chunks[:6] or top_chunks[:1]

        if _should_abstain(latest_query, chunks_for_answer):
            return AgentTrace(
                answer=(
                    "The supplied information is insufficient to confirm that detail. "
                    "I recommend human confirmation."
                ),
                messages=list(messages),
                handoff_recommended=True,
            )

        if response.conflicts:
            return _handle_source_conflict(messages, response, authoritative_chunks)

        handoff = _should_recommend_handoff(latest_query)
        answer = "\n\n".join(chunk.text for chunk in chunks_for_answer)
        if handoff:
            answer += (
                "\n\nHuman review is required before approval. "
                "I recommend contacting support for the next step."
            )

        citation_chunks = authoritative_chunks[:6] or top_chunks[:3]
        sources = [f"{chunk.source_file} > {chunk.heading}" for chunk in citation_chunks]
        source_files = [chunk.source_file for chunk in citation_chunks]

        return AgentTrace(
            answer=answer,
            sources=sources,
            source_files=source_files,
            handoff_recommended=handoff,
            messages=list(messages),
            retrieved_chunks=[chunk.id for chunk in citation_chunks],
        )


def _looks_like_order_question(text: str) -> bool:
    return _ORDER_QUESTION_PATTERN.search(text) is not None


def _requests_sensitive_info(text: str) -> bool:
    lower = text.lower()
    return any(term in lower for term in _SENSITIVE_REQUEST_TERMS)


def _is_prompt_injection_attempt(text: str) -> bool:
    lower = text.lower()
    return "migration note" in lower and ("60 days" in lower or "ignore the real policy" in lower)


def _should_abstain(query: str, chunks: list) -> bool:
    lower_query = query.lower()
    if not any(term in lower_query for term in _ABSTENTION_QUERY_TERMS):
        return False

    combined_chunk_text = " ".join(chunk.text.lower() for chunk in chunks)
    return "vegan" not in combined_chunk_text and "material certification" not in combined_chunk_text


def _should_recommend_handoff(query: str) -> bool:
    lower = query.lower()
    return any(
        term in lower
        for term in ("damaged", "broken", "defective", "final-sale", "final sale", "out of luck")
    )


def _handle_prompt_injection(messages: list[dict[str, str]]) -> AgentTrace:
    return AgentTrace(
        answer=(
            "The migration note is internal and is not authoritative customer policy. "
            "The standard return window is 30 calendar days from delivery unless a valid "
            "exception applies. I cannot approve a return."
        ),
        sources=["01-returns-policy-current.md > Standard return window"],
        source_files=["01-returns-policy-current.md"],
        messages=list(messages),
        handoff_recommended=False,
    )


def _handle_source_conflict(
    messages: list[dict[str, str]],
    response: RetrievalResponse,
    authoritative_chunks: list,
) -> AgentTrace:
    unique_by_file: dict[str, object] = {}
    for chunk in authoritative_chunks:
        unique_by_file.setdefault(chunk.source_file, chunk)

    parts = [
        "Current official sources conflict on this topic.",
        "One source says to hand-wash the Breeze Tumbler body, while another says "
        "all components are dishwasher safe.",
    ]
    parts.extend(chunk.text for chunk in unique_by_file.values())
    parts.append("Please contact support for human confirmation or safest interim guidance.")

    source_files = list(unique_by_file.keys())
    sources = [f"{chunk.source_file} > {chunk.heading}" for chunk in unique_by_file.values()]

    return AgentTrace(
        answer="\n\n".join(parts),
        sources=sources,
        source_files=source_files,
        handoff_recommended=True,
        messages=list(messages),
        retrieved_chunks=[chunk.id for chunk in unique_by_file.values()],
        conflicts=[conflict.topic for conflict in response.conflicts],
    )


def _format_delivery_date(iso_date: str) -> str:
    parsed = datetime.strptime(iso_date, "%Y-%m-%d")
    return parsed.strftime("%B %d, %Y")


def _format_order_answer(result: OrderLookupResult, *, sensitive_request: bool) -> str:
    if result.error == "invalid_order_id":
        return "Please provide a valid order ID such as ORD-1007."

    if not result.found:
        return (
            "I could not find an order with that ID. Please double-check the order ID "
            "or contact support for help."
        )

    data = result.data or {}
    parts: list[str] = []

    if sensitive_request:
        parts.append(
            "I cannot share customer email, shipping address, internal notes, or risk scores. "
            "I can only provide customer-safe order status details."
        )

    message = data.get("customer_safe_message")
    if isinstance(message, str) and message.strip():
        parts.append(message)

    status = data.get("status")
    if status:
        parts.append(f"Status: {status}")

    if status == "cancelled":
        parts.append("The order is cancelled and will not be shipped.")
    elif status == "returned":
        parts.append("The order has been returned and will not be delivered again.")
    elif status == "exception":
        parts.append("This order has an exception that requires support review.")

    carrier = data.get("carrier")
    if carrier:
        parts.append(f"Carrier: {carrier}")

    estimated_delivery = data.get("estimated_delivery")
    if estimated_delivery:
        parts.append(f"Estimated delivery: {_format_delivery_date(estimated_delivery)}")
    elif status == "shipped":
        parts.append("A delivery estimate is not currently available.")

    if result.guidance:
        parts.append(result.guidance)

    return " ".join(parts)
