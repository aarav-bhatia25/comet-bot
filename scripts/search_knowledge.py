#!/usr/bin/env python3
"""Search the knowledge base from the command line."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

from comet_bot.retrieval import KnowledgeIndex  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Semantic search over the knowledge base.")
    parser.add_argument("query", help="Search query text")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results to return")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON output",
    )
    args = parser.parse_args()

    index = KnowledgeIndex.build()
    response = index.search(args.query, top_k=args.top_k)

    if args.json:
        payload = {
            "query": response.query,
            "conflicts": [
                {
                    "topic": conflict.topic,
                    "source_files": list(conflict.source_files),
                    "description": conflict.description,
                }
                for conflict in response.conflicts
            ],
            "results": [
                {
                    "source_file": result.chunk.source_file,
                    "heading": result.chunk.heading,
                    "heading_path": result.chunk.heading_path,
                    "is_authoritative": result.chunk.metadata.get("is_authoritative"),
                    "similarity_score": round(result.similarity_score, 4),
                    "metadata_boost": round(result.metadata_boost, 4),
                    "keyword_boost": round(result.keyword_boost, 4),
                    "final_score": round(result.final_score, 4),
                }
                for result in response.results
            ],
        }
        print(json.dumps(payload, indent=2))
        return 0

    print(f'Query: "{response.query}"\n')

    if response.conflicts:
        print("Conflicts detected:")
        for conflict in response.conflicts:
            print(f"  - {conflict.topic}: {', '.join(conflict.source_files)}")
            print(f"    {conflict.description}")
        print()

    if not response.results:
        print("No results.")
        return 0

    for rank, result in enumerate(response.results, start=1):
        preview = result.chunk.text.replace("\n", " ")
        if len(preview) > 140:
            preview = preview[:137] + "..."

        print(f"{rank}. [{result.chunk.source_file} > {result.chunk.heading}]")
        print(
            "   "
            f"score={result.final_score:.4f} "
            f"(sim={result.similarity_score:.4f}, "
            f"meta={result.metadata_boost:+.2f}, "
            f"kw={result.keyword_boost:.2f}) "
            f"authoritative={result.chunk.metadata.get('is_authoritative')}"
        )
        print(f"   {preview}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
