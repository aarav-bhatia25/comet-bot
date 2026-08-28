"""FastAPI application serving the support chat UI."""

from __future__ import annotations

import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from openai import APIConnectionError, APIError, RateLimitError
from pydantic import BaseModel, Field, field_validator

from comet_bot.agent import SessionStore, SupportAgent

STATIC_DIR = Path(__file__).resolve().parent / "static"


class ChatRequest(BaseModel):
    message: str = Field(max_length=4000)
    session_id: str | None = None

    @field_validator("message")
    @classmethod
    def message_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("message must not be empty")
        return stripped


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    sources: list[str]
    source_files: list[str]
    handoff_recommended: bool
    tool_calls: list[dict[str, Any]]


class SessionResponse(BaseModel):
    session_id: str


def _trace_to_response(session_id: str, trace) -> ChatResponse:
    return ChatResponse(
        session_id=session_id,
        answer=trace.answer,
        sources=trace.sources,
        source_files=trace.primary_source_files,
        handoff_recommended=trace.handoff_recommended,
        tool_calls=[asdict(call) for call in trace.tool_calls],
    )


def create_app(
    *,
    agent: SupportAgent | None = None,
    sessions: SessionStore | None = None,
) -> FastAPI:
    """Build the FastAPI app. Dependencies are injectable for tests."""
    app = FastAPI(title="Aster & Row Support", version="0.1.0")
    support_agent = agent
    session_store = sessions or SessionStore()

    def _get_agent() -> SupportAgent:
        nonlocal support_agent
        if support_agent is None:
            support_agent = SupportAgent()
        return support_agent

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.post("/api/sessions", response_model=SessionResponse)
    async def create_session() -> SessionResponse:
        session_id = str(uuid.uuid4())
        session_store.get(session_id)
        return SessionResponse(session_id=session_id)

    @app.post("/api/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest) -> ChatResponse:
        session_id = request.session_id or str(uuid.uuid4())
        session = session_store.get(session_id)
        session.append("user", request.message)

        try:
            trace = _get_agent().run(session.messages, session_id=session_id)
        except (APIConnectionError, RateLimitError, APIError) as exc:
            session.messages.pop()
            raise HTTPException(
                status_code=503,
                detail=f"Could not reach the model ({exc.__class__.__name__}).",
            ) from exc

        session.append("assistant", trace.answer)
        return _trace_to_response(session_id, trace)

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app
