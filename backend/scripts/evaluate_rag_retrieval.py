from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv

load_dotenv(BACKEND_DIR / ".env")
load_dotenv(BACKEND_DIR / ".env.cloudrun", override=True)

from app.core.ai_providers import build_embeddings
from app.core.retrieval_filters import infer_retrieval_filter
from app.core.vector_store import QdrantDocumentStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare lexical, dense, and hybrid retrieval against a JSONL gold set."
    )
    parser.add_argument(
        "--eval-set",
        type=Path,
        default=BACKEND_DIR / "data" / "rag_retrieval_eval.jsonl",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=BACKEND_DIR / "data" / "rag_retrieval_eval_results.json",
    )
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--embedding-provider", default=os.getenv("EMBEDDING_PROVIDER", "cloudflare"))
    parser.add_argument("--coverage-only", action="store_true", help="Only inspect metadata coverage.")
    return parser.parse_args()


def load_eval_set(path: Path) -> list[dict[str, Any]]:
    cases = []
    seen_ids: set[str] = set()
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                case = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
            if not isinstance(case, dict):
                raise ValueError(f"{path}:{line_number}: each JSONL row must be an object")
            if not isinstance(case.get("id"), str) or not case["id"].strip():
                raise ValueError(f"{path}:{line_number}: id must be a non-empty string")
            if case["id"] in seen_ids:
                raise ValueError(f"{path}:{line_number}: duplicate id {case['id']!r}")
            if not isinstance(case.get("query"), str) or not case["query"].strip():
                raise ValueError(f"{path}:{line_number}: query must be a non-empty string")
            expected = case.get("expected")
            if not isinstance(expected, dict) or not any(
                expected.get(key) for key in ("sources", "title_contains", "content_contains")
            ):
                raise ValueError(f"{path}:{line_number}: expected must contain a source or term")
            seen_ids.add(case["id"])
            cases.append(case)
    if not cases:
        raise ValueError(f"No evaluation cases found in {path}")
    return cases


def document_key(document: Any) -> str:
    metadata = document.metadata or {}
    return str(
        metadata.get("_retrieval_point_id")
        or f"{metadata.get('source', '')}|{metadata.get('title', '')}|{document.page_content[:120]}"
    )


def matches_expected(document: Any, expected: dict[str, Any]) -> bool:
    metadata = document.metadata or {}
    source = str(metadata.get("source") or "")
    allowed_sources = expected.get("sources") or []
    if allowed_sources and source not in allowed_sources:
        return False

    title_terms = expected.get("title_contains") or []
    content_terms = expected.get("content_contains") or []
    title = str(metadata.get("title") or metadata.get("event") or "")
    content = document.page_content or ""
    if title_terms and not any(term.casefold() in title.casefold() for term in title_terms):
        return False
    if content_terms and not any(term.casefold() in content.casefold() for term in content_terms):
        return False
    return bool(allowed_sources or title_terms or content_terms)


def summarize_documents(documents: list[Any]) -> list[dict[str, Any]]:
    output = []
    for rank, document in enumerate(documents, start=1):
        metadata = document.metadata or {}
        output.append(
            {
                "rank": rank,
                "point_id": metadata.get("_retrieval_point_id"),
                "source": metadata.get("source"),
                "title": metadata.get("title") or metadata.get("event"),
                "category": metadata.get("category"),
                "preview": " ".join(document.page_content.split())[:220],
            }
        )
    return output


def merge_unique_documents(
    primary: list[Any],
    secondary: list[Any],
    *,
    limit: int,
) -> list[Any]:
    """Merge filtered and unfiltered results in production order without duplicates."""
    merged: list[Any] = []
    seen: set[str] = set()
    for document in [*primary, *secondary]:
        key = document_key(document)
        if key in seen:
            continue
        seen.add(key)
        merged.append(document)
        if len(merged) >= limit:
            break
    return merged


def filter_coverage(
    cases: list[dict[str, Any]], metadata_coverage: dict[str, Any]
) -> dict[str, Any]:
    candidates: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        for field, value in (case.get("filter_candidates") or {}).items():
            value_label = json.dumps(value, ensure_ascii=False, sort_keys=True)
            candidates[f"{field}={value_label}"].append(case)

    report = {}
    for label, rows in candidates.items():
        field, raw_value = label.split("=", 1)
        try:
            candidate_value = json.loads(raw_value)
        except json.JSONDecodeError:
            candidate_value = raw_value
        by_source = metadata_coverage.get("by_source", {})
        supported_cases: list[str] = []
        missing_cases: list[str] = []
        for case in rows:
            sources = case.get("expected", {}).get("sources") or list(by_source)
            source_support = []
            for source in sources:
                source_data = by_source.get(source, {})
                field_data = source_data.get("fields", {}).get(field, {})
                value_count = field_data.get("values", {}).get(
                    json.dumps(candidate_value, ensure_ascii=False, sort_keys=True), 0
                )
                source_support.append(
                    field_data.get("coverage", 0) >= (1.0 if case.get("require_complete_filter") else 0.95)
                    and value_count > 0
                )
            if source_support and all(source_support):
                supported_cases.append(case["id"])
            else:
                missing_cases.append(case["id"])
        covered = len(supported_cases)
        fraction = covered / len(rows) if rows else 0
        strict = any(case.get("require_complete_filter") for case in rows)
        threshold = 1.0 if strict else 0.95
        report[label] = {
            "cases": len(rows),
            "metadata_supported_cases": covered,
            "case_coverage": fraction,
            "threshold": threshold,
            "eligible": fraction >= threshold,
            "unsupported_case_ids": missing_cases,
            "basis": "global metadata coverage within each expected source; validate relevance before enabling filters",
        }
    return report


def evaluate_filter_routing(cases: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    exact_matches = 0
    for case in cases:
        expected_filter = dict(case.get("filter_candidates") or {})
        decision = infer_retrieval_filter(case["query"])
        exact_match = decision.metadata_filter == expected_filter
        if exact_match:
            exact_matches += 1
        rows.append(
            {
                "id": case["id"],
                "query": case["query"],
                "expected_filter": expected_filter,
                "inferred_filter": decision.metadata_filter,
                "confidence": decision.confidence,
                "reasons": list(decision.reasons),
                "exact_match": exact_match,
            }
        )

    return {
        "case_count": len(cases),
        "exact_matches": exact_matches,
        "exact_match_rate": exact_matches / len(cases) if cases else 0,
        "mismatches": [row for row in rows if not row["exact_match"]],
        "decisions": rows,
    }


def main() -> int:
    args = parse_args()
    if args.top_k <= 0:
        raise ValueError("--top-k must be positive")
    cases = load_eval_set(args.eval_set)
    report: dict[str, Any] = {
        "eval_set": str(args.eval_set),
        "top_k": args.top_k,
        "case_count": len(cases),
        "status": "ok",
        "filter_routing": evaluate_filter_routing(cases),
    }

    try:
        from app.core.ai_providers import require_env

        store = QdrantDocumentStore(
            url=require_env("QDRANT_URL"),
            api_key=require_env("QDRANT_API_KEY"),
            collection_name=os.getenv("QDRANT_COLLECTION", "knu-campus-bge-m3"),
            embeddings=None if args.coverage_only else build_embeddings(args.embedding_provider),
            search_limit=args.top_k,
            lexical_weight=float(os.getenv("QDRANT_LEXICAL_WEIGHT", "0.25")),
            vector_weight=float(os.getenv("QDRANT_VECTOR_WEIGHT", "0.75")),
        )
        report["collection"] = store.collection_name
        report["fusion_weights"] = {
            "lexical": store.lexical_weight,
            "vector": store.vector_weight,
        }
        report["fusion_strategy"] = "dense_top_k_guarded_weighted_rrf"
        report["filter_evaluation"] = {
            "modes": {
                "candidate_filtered_hybrid": "filter_candidates annotated in each evaluation case",
                "routed_filtered_hybrid": "filter inferred from each question; unfiltered hybrid when no hard filter is inferred",
                "routed_filtered_hybrid_with_fallback": "routed search supplemented with unfiltered hybrid results when filtered results are fewer than top-k",
            },
            "production_routing_required": False,
            "execution": "Qdrant server-side payload filtering for lexical and vector retrieval",
            "payload_indexes_required_for_production": [
                "metadata.source",
                "metadata.category",
                "metadata.academic_year",
            ],
        }
        report["metadata_coverage"] = store.metadata_coverage()
        if args.coverage_only:
            report["retrieval"] = {"status": "skipped", "reason": "coverage-only"}
        else:
            gold_counts = Counter()
            for document in store.iter_documents():
                for case in cases:
                    if matches_expected(document, case["expected"]):
                        gold_counts[case["id"]] += 1
            missing_gold = [
                case for case in cases if gold_counts[case["id"]] == 0
            ]
            valid_cases = [
                case for case in cases if gold_counts[case["id"]] > 0
            ]
            report["gold_validation"] = {
                "valid": [case["id"] for case in valid_cases],
                "missing": [
                    {"id": case["id"], "expected": case["expected"]}
                    for case in missing_gold
                ],
                "duplicate_matches": {
                    case["id"]: gold_counts[case["id"]]
                    for case in cases
                    if gold_counts[case["id"]] > 1
                },
            }
            if missing_gold:
                report["status"] = "error"
            modes = (
                "lexical",
                "vector",
                "legacy_hybrid",
                "hybrid",
                "candidate_filtered_hybrid",
                "routed_filtered_hybrid",
                "routed_filtered_hybrid_with_fallback",
            )
            per_mode_hits = Counter()
            misses: dict[str, list[dict[str, Any]]] = {mode: [] for mode in modes}
            comparisons = []
            for case in valid_cases:
                try:
                    query_vector = store.embeddings.embed_query(case["query"])
                    results = store.search_diagnostics(
                        case["query"],
                        ensure_text_index=False,
                        query_vector=query_vector,
                    )
                    candidate_filter = dict(case.get("filter_candidates") or {})
                    filtered_results = store.search_diagnostics(
                        case["query"],
                        ensure_text_index=False,
                        metadata_filter=candidate_filter,
                        query_vector=query_vector,
                    )
                    decision = infer_retrieval_filter(case["query"])
                    inferred_filter = dict(decision.metadata_filter)
                    if decision.confidence == "high" and inferred_filter:
                        routed_results = store.search_diagnostics(
                            case["query"],
                            ensure_text_index=False,
                            metadata_filter=inferred_filter,
                            query_vector=query_vector,
                        )
                        routed_filtered = routed_results["hybrid"][: args.top_k]
                        fallback_used = len(routed_filtered) < args.top_k
                        routed_with_fallback = (
                            merge_unique_documents(
                                routed_filtered,
                                results["hybrid"][: args.top_k],
                                limit=args.top_k,
                            )
                            if fallback_used
                            else routed_filtered
                        )
                        filtered_result_count = len(routed_filtered)
                    else:
                        routed_filtered = results["hybrid"][: args.top_k]
                        routed_with_fallback = routed_filtered
                        filtered_result_count = 0
                        fallback_used = False
                    trimmed = {
                        mode: results[mode][: args.top_k]
                        for mode in ("lexical", "vector", "legacy_hybrid", "hybrid")
                    }
                    trimmed["candidate_filtered_hybrid"] = filtered_results["hybrid"][
                        : args.top_k
                    ]
                    trimmed["routed_filtered_hybrid"] = routed_filtered
                    trimmed["routed_filtered_hybrid_with_fallback"] = routed_with_fallback
                    matched_by_mode = {
                        mode: [doc for doc in trimmed[mode] if matches_expected(doc, case["expected"])]
                        for mode in modes
                    }
                    for mode in modes:
                        if matched_by_mode[mode]:
                            per_mode_hits[mode] += 1
                        else:
                            misses[mode].append(
                                {
                                    "id": case["id"],
                                    "query": case["query"],
                                    "expected": case["expected"],
                                    "results": summarize_documents(trimmed[mode]),
                                }
                            )
                    identities = {
                        mode: {document_key(doc) for doc in trimmed[mode]}
                        for mode in modes
                    }
                    hybrid_gained = identities["hybrid"] - identities["legacy_hybrid"]
                    hybrid_lost = identities["legacy_hybrid"] - identities["hybrid"]
                    comparisons.append(
                        {
                            "id": case["id"],
                            "query": case["query"],
                            "type": case.get("type"),
                            "expected": case["expected"],
                            "candidate_filter": candidate_filter,
                            "filter_decision": {
                                "metadata_filter": inferred_filter,
                                "confidence": decision.confidence,
                                "reasons": list(decision.reasons),
                            },
                            "filtered_result_count": filtered_result_count,
                            "fallback_used": fallback_used,
                            "hits": {mode: bool(matched_by_mode[mode]) for mode in modes},
                            "only_in_lexical": sorted(identities["lexical"] - identities["vector"]),
                            "only_in_vector": sorted(identities["vector"] - identities["lexical"]),
                            "only_in_hybrid": sorted(identities["hybrid"] - (identities["lexical"] | identities["vector"])),
                            "hybrid_gained_vs_legacy": sorted(hybrid_gained),
                            "hybrid_lost_vs_legacy": sorted(hybrid_lost),
                            "results": {mode: summarize_documents(trimmed[mode]) for mode in modes},
                        }
                    )
                except Exception as exc:
                    report.setdefault("case_errors", []).append(
                        {
                            "id": case["id"],
                            "query": case["query"],
                            "failed_modes": list(modes),
                            "error": str(exc),
                        }
                    )

            report["retrieval"] = {
                "status": "error" if report.get("case_errors") or missing_gold else "ok",
                "recall_at_k": {
                    mode: per_mode_hits[mode] / len(valid_cases) if valid_cases else 0
                    for mode in modes
                },
                "valid_case_count": len(valid_cases),
                "hits": dict(per_mode_hits),
                "misses": misses,
                "comparisons": comparisons,
                "metadata_filter_candidates": filter_coverage(valid_cases, report["metadata_coverage"]),
                "hybrid_delta": {
                    "recovered_case_ids": [
                        comparison["id"]
                        for comparison in comparisons
                        if comparison["hits"]["hybrid"]
                        and not comparison["hits"]["legacy_hybrid"]
                    ],
                    "regressed_case_ids": [
                        comparison["id"]
                        for comparison in comparisons
                        if comparison["hits"]["legacy_hybrid"]
                        and not comparison["hits"]["hybrid"]
                    ],
                },
                "filter_delta": {
                    "recovered_case_ids": [
                        comparison["id"]
                        for comparison in comparisons
                        if comparison["hits"]["candidate_filtered_hybrid"]
                        and not comparison["hits"]["hybrid"]
                    ],
                    "regressed_case_ids": [
                        comparison["id"]
                        for comparison in comparisons
                        if comparison["hits"]["hybrid"]
                        and not comparison["hits"]["candidate_filtered_hybrid"]
                    ],
                },
                "routed_filter_delta": {
                    "recovered_case_ids": [
                        comparison["id"]
                        for comparison in comparisons
                        if comparison["hits"]["routed_filtered_hybrid"]
                        and not comparison["hits"]["hybrid"]
                    ],
                    "regressed_case_ids": [
                        comparison["id"]
                        for comparison in comparisons
                        if comparison["hits"]["hybrid"]
                        and not comparison["hits"]["routed_filtered_hybrid"]
                    ],
                },
                "routed_fallback_delta": {
                    "recovered_case_ids": [
                        comparison["id"]
                        for comparison in comparisons
                        if comparison["hits"]["routed_filtered_hybrid_with_fallback"]
                        and not comparison["hits"]["hybrid"]
                    ],
                    "regressed_case_ids": [
                        comparison["id"]
                        for comparison in comparisons
                        if comparison["hits"]["hybrid"]
                        and not comparison["hits"]["routed_filtered_hybrid_with_fallback"]
                    ],
                    "fallback_case_ids": [
                        comparison["id"]
                        for comparison in comparisons
                        if comparison["fallback_used"]
                    ],
                },
            }
            if report.get("case_errors") or missing_gold:
                report["status"] = "error"
    except Exception as exc:
        report["status"] = "error"
        report["error"] = str(exc)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "output": str(args.output),
        "collection": report.get("collection"),
        "fusion_weights": report.get("fusion_weights"),
        "fusion_strategy": report.get("fusion_strategy"),
        "filter_evaluation": report.get("filter_evaluation"),
        "filter_routing": {
            "exact_matches": (report.get("filter_routing") or {}).get("exact_matches"),
            "case_count": (report.get("filter_routing") or {}).get("case_count"),
            "exact_match_rate": (report.get("filter_routing") or {}).get(
                "exact_match_rate"
            ),
            "mismatch_case_ids": [
                row["id"]
                for row in (report.get("filter_routing") or {}).get("mismatches", [])
            ],
        },
        "total_points": (report.get("metadata_coverage") or {}).get("total_points"),
        "recall_at_k": (report.get("retrieval") or {}).get("recall_at_k"),
        "hybrid_delta": (report.get("retrieval") or {}).get("hybrid_delta"),
        "filter_delta": (report.get("retrieval") or {}).get("filter_delta"),
        "routed_filter_delta": (report.get("retrieval") or {}).get(
            "routed_filter_delta"
        ),
        "routed_fallback_delta": (report.get("retrieval") or {}).get(
            "routed_fallback_delta"
        ),
        "missing_gold_count": len((report.get("gold_validation") or {}).get("missing", [])),
        "filter_candidates": (report.get("retrieval") or {}).get("metadata_filter_candidates"),
        "error": report.get("error"),
    }, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
