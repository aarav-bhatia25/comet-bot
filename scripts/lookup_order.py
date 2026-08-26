#!/usr/bin/env python3
"""Look up a single order from the command line."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

from comet_bot.tools import lookup_order  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Sanitized order lookup.")
    parser.add_argument("order_id", help="Order ID such as ORD-1007")
    args = parser.parse_args()

    result = lookup_order(args.order_id)
    print(json.dumps(result.to_tool_dict(), indent=2))
    return 0 if result.found or result.error == "invalid_order_id" else 1


if __name__ == "__main__":
    raise SystemExit(main())
