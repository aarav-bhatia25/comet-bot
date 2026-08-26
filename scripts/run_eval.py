#!/usr/bin/env python3
"""Run the evaluation suite against the current agent implementation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

from comet_bot.agent import RetrievalEvalAgent  # noqa: E402
from comet_bot.eval import run_evaluation  # noqa: E402


def _print_report(report) -> None:
    print(f"Evaluation results: {report.passed}/{report.total} passed\n")

    print("By category:")
    for summary in report.category_summaries:
        print(f"  {summary.category:<22} {summary.passed}/{summary.total}")
    print()

    for result in report.case_results:
        status = "PASS" if result.passed else "FAIL"
        print(f"[{status}] {result.case_id} ({result.category})")
        if result.answer_preview:
            print(f"  answer: {result.answer_preview}")
        if not result.passed:
            for assertion in result.assertions:
                if not assertion.passed:
                    print(f"  - {assertion.name}: {assertion.detail}")
        print()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run visible and custom evaluation cases.")
    parser.add_argument("--category", help="Run only one category")
    parser.add_argument("--visible-only", action="store_true", help="Skip custom cases")
    parser.add_argument("--custom-only", action="store_true", help="Skip visible cases")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON output")
    args = parser.parse_args()

    agent = RetrievalEvalAgent()
    report = run_evaluation(
        agent,
        include_visible=not args.custom_only,
        include_custom=not args.visible_only,
        category=args.category,
    )

    if args.json:
        payload = {
            "passed": report.passed,
            "total": report.total,
            "categories": [
                {
                    "category": summary.category,
                    "passed": summary.passed,
                    "total": summary.total,
                }
                for summary in report.category_summaries
            ],
            "cases": [
                {
                    "id": result.case_id,
                    "category": result.category,
                    "passed": result.passed,
                    "answer_preview": result.answer_preview,
                    "failed_assertions": [
                        {"name": assertion.name, "detail": assertion.detail}
                        for assertion in result.assertions
                        if not assertion.passed
                    ],
                }
                for result in report.case_results
            ],
        }
        print(json.dumps(payload, indent=2))
    else:
        _print_report(report)

    return 0 if report.all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
