#!/usr/bin/env python3
"""Interactive CLI for the Aster & Row support agent."""

from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

from openai import APIConnectionError, APIError, RateLimitError

from comet_bot.agent import SessionStore, SupportAgent  # noqa: E402


def _print_response(trace) -> None:
    print(f"\nAnswer:\n{trace.answer}\n")

    if trace.sources:
        print("Sources:")
        for source in trace.sources:
            print(f"  - {source}")
        print()

    print(f"Handoff recommended: {'yes' if trace.handoff_recommended else 'no'}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Chat with the Aster & Row support agent.")
    parser.add_argument(
        "--session-id",
        default=str(uuid.uuid4()),
        help="Conversation session identifier",
    )
    args = parser.parse_args()

    agent = SupportAgent()
    sessions = SessionStore()
    session = sessions.get(args.session_id)

    print("Aster & Row Support Agent")
    print(f"Session: {args.session_id}")
    print("Type 'exit' or 'quit' to end.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            return 0

        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye.")
            return 0

        session.append("user", user_input)
        try:
            trace = agent.run(session.messages, session_id=session.session_id)
        except (APIConnectionError, RateLimitError, APIError) as exc:
            session.messages.pop()
            print(f"\nError: could not reach the model ({exc.__class__.__name__}). Please try again.\n")
            continue

        session.append("assistant", trace.answer)
        _print_response(trace)


if __name__ == "__main__":
    raise SystemExit(main())
