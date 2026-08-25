#!/usr/bin/env python3
"""Print all knowledge-base chunks for manual inspection."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

from comet_bot.ingest import load_chunks  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Print chunked knowledge-base sections.")
    parser.add_argument(
        "--file",
        help="Show chunks from one file only (e.g. 01-returns-policy-current.md)",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=0,
        help="Print only the first N chunks (0 = print all)",
    )
    args = parser.parse_args()

    chunks = load_chunks()

    if args.file:
        chunks = [chunk for chunk in chunks if chunk.source_file == args.file]
        if not chunks:
            print(f"No chunks found for file: {args.file}")
            return 1

    counts = Counter(chunk.source_file for chunk in chunks)
    print(f"Loaded {len(counts)} files -> {len(chunks)} chunks\n")

    for source_file, count in sorted(counts.items()):
        print(f"  {source_file}: {count} chunks")

    print("\n" + "=" * 72 + "\n")

    display_chunks = chunks[: args.sample] if args.sample > 0 else chunks
    for chunk in display_chunks:
        status = chunk.metadata.get("status", "unknown")
        authority = chunk.metadata.get("policy_authority", "unknown")
        preview = chunk.text.replace("\n", " ")
        if len(preview) > 160:
            preview = preview[:157] + "..."

        print(f"[{chunk.source_file} > {chunk.heading}]")
        print(f"  id:       {chunk.id}")
        print(f"  status:   {status} | authority: {authority} | authoritative: {chunk.metadata.get('is_authoritative')}")
        print(f"  preview:  {preview}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
