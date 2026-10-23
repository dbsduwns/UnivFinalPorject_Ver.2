from types import SimpleNamespace

import pytest

from scripts.evaluate_rag_retrieval import filter_coverage, load_eval_set, matches_expected


def _document(source="공지사항", title="국가장학금 신청 안내", content="장학 공지"):
    return SimpleNamespace(
        metadata={"source": source, "title": title},
        page_content=content,
    )


def test_matches_expected_uses_source_and_title_terms():
    expected = {"sources": ["공지사항"], "title_contains": ["국가장학금", "교내장학"]}

    assert matches_expected(_document(), expected)
    assert not matches_expected(_document(source="학사일정"), expected)
    assert not matches_expected(_document(title="수강신청 안내"), expected)


def test_filter_coverage_requires_field_population_and_candidate_value():
    cases = [
        {
            "id": "notice-1",
            "expected": {"sources": ["공지사항"]},
            "filter_candidates": {"source": "공지사항", "category": "장학"},
        },
        {
            "id": "notice-2",
            "expected": {"sources": ["공지사항"]},
            "filter_candidates": {"source": "공지사항", "category": "장학"},
        },
    ]
    coverage = {
        "by_source": {
            "공지사항": {
                "fields": {
                    "source": {
                        "coverage": 1.0,
                        "values": {'"공지사항"': 2},
                    },
                    "category": {
                        "coverage": 0.9,
                        "values": {'"장학"': 2},
                    },
                }
            }
        }
    }

    results = filter_coverage(cases, coverage)

    assert results['source="공지사항"']["eligible"]
    assert not results['category="장학"']["eligible"]


def test_load_eval_set_rejects_duplicate_ids(tmp_path):
    path = tmp_path / "cases.jsonl"
    case = '{"id":"same","query":"질문","expected":{"sources":["공지사항"]}}\n'
    path.write_text(case + case, encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate id"):
        load_eval_set(path)
