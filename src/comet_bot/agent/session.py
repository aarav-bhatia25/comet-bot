"""In-memory conversation session storage for interactive chat."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ConversationSession:
    """Stores message history for one chat session."""

    session_id: str
    messages: list[dict[str, str]] = field(default_factory=list)

    def append(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})


class SessionStore:
    """Simple in-memory store keyed by session ID."""

    def __init__(self) -> None:
        self._sessions: dict[str, ConversationSession] = {}

    def get(self, session_id: str) -> ConversationSession:
        if session_id not in self._sessions:
            self._sessions[session_id] = ConversationSession(session_id=session_id)
        return self._sessions[session_id]
