"""Evaluate FAQ retrieval with search_faq_knowledgebase (search_knowledge).

Uses `evals/datasets/retrieval_eval_dataset.json`: each synthetic question
should retrieve the gold `content` chunk. Reports hit@1, hit@k, and MRR.

    uv run python evals/evaluate_knowledge_search.py --search-type genai_001_embedding
    uv run python evals/evaluate_knowledge_search.py --search-type genai_001_embedding --top-k 5
    uv run python evals/evaluate_knowledge_search.py --search-type genai_001_embedding --document-id <google-doc-id>
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from ecommerce_agent.config import PROJECT_ROOT
from ecommerce_agent.tools.knowledge import search_faq_knowledgebase

DEFAULT_DATASET = PROJECT_ROOT / "evals" / "datasets" / "retrieval_eval_dataset.json"
DEFAULT_TOP_K = 5


def search_knowledge(
    query: str,
    document_id: str | None = None,
    top_k: int = DEFAULT_TOP_K,
) -> dict[str, Any]:
    """Call the knowledge-base search tool (unwraps the Agents SDK FunctionTool)."""
    return search_faq_knowledgebase.__wrapped__(
        query, document_id=document_id, top_k=top_k
    )


def load_dataset(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise ValueError(f"{path} must be a non-empty JSON array")
    return payload


def _norm(text: str) -> str:
    return " ".join(text.split()).casefold()


def rank_of_expected(expected: str, results: list[dict[str, Any]]) -> int | None:
    needle = _norm(expected)
    if not needle:
        return None
    for index, row in enumerate(results, start=1):
        haystack = _norm(str(row.get("content") or ""))
        if needle in haystack or haystack in needle:
            return index
    return None


def summarize(ranks: list[int | None], k: int) -> dict[str, float | int]:
    n = len(ranks)
    if n == 0:
        return {"n": 0, "hit_at_1": 0.0, "hit_at_k": 0.0, "mrr": 0.0}
    return {
        "n": n,
        "hit_at_1": sum(rank == 1 for rank in ranks) / n,
        "hit_at_k": sum(rank is not None and rank <= k for rank in ranks) / n,
        "mrr": sum((1 / rank) if rank else 0.0 for rank in ranks) / n,
    }


def evaluate_row(
    record: dict[str, Any],
    top_k: int = DEFAULT_TOP_K,
    document_id: str | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    payload = search_knowledge(
        record["synthetic_question"],
        document_id=document_id,
        top_k=top_k,
    )
    latency_ms = (time.perf_counter() - started) * 1000
    results = []
    status = "success"
    if isinstance(payload, dict):
        status = str(payload.get("status") or "success")
        results = list(payload.get("results") or [])
    rank = rank_of_expected(record["content"], results)
    return {
        "id": record["id"],
        "synthetic_question": record["synthetic_question"],
        "rank": rank,
        "hit_at_1": rank == 1,
        "hit_at_k": rank is not None and rank <= top_k,
        "status": status,
        "latency_ms": latency_ms,
    }


def run_eval(
    dataset_path: Path = DEFAULT_DATASET,
    top_k: int = DEFAULT_TOP_K,
    document_id: str | None = None,
) -> dict[str, Any]:
    records = load_dataset(dataset_path)
    rows = [
        evaluate_row(record, top_k=top_k, document_id=document_id)
        for record in records
    ]
    metrics = summarize([row["rank"] for row in rows], k=top_k)
    latencies = [row["latency_ms"] for row in rows]
    metrics["latency_ms"] = (sum(latencies) / len(latencies)) if latencies else 0.0
    return {
        "rows": rows,
        "metrics": metrics,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate knowledge-base search hit@k and MRR."
    )
    parser.add_argument(
        "--search-type",
        required=True,
        help='Label for this retrieval setup, e.g. "genai_001_embedding".',
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET,
        help="Retrieval eval JSON (id, content, synthetic_question).",
    )
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument(
        "--document-id",
        default=None,
        help="Optional knowledge-base document_id. Omit when only one doc exists.",
    )
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    report = run_eval(
        dataset_path=args.dataset,
        top_k=args.top_k,
        document_id=args.document_id,
    )
    metrics = report["metrics"]
    print(
        f"search_type={args.search_type}  n={metrics['n']}  "
        f"hit@1={metrics['hit_at_1']:.3f}  "
        f"hit@{args.top_k}={metrics['hit_at_k']:.3f}  mrr={metrics['mrr']:.3f}  "
        f"latency_ms={metrics['latency_ms']:.1f}"
    )
    misses = [row for row in report["rows"] if not row["hit_at_k"]]
    if misses:
        print(f"misses ({len(misses)}):")
        for row in misses:
            print(f"  id={row['id']}  {row['synthetic_question']}")


if __name__ == "__main__":
    main()
