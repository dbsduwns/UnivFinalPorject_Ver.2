"""사용자 질문에서 안전하게 적용할 수 있는 RAG 메타데이터 필터를 판별합니다."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from typing import Literal

from qdrant_client.models import FieldCondition, Filter, MatchValue

FilterConfidence = Literal["high", "none"]


@dataclass(frozen=True)
class RetrievalFilterDecision:
    metadata_filter: dict[str, str | int]
    confidence: FilterConfidence
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


SHUTTLE_TERMS = (
    "셔틀",
    "통학버스",
    "기흥역",
    "이공관",
)

MEAL_TERMS = (
    "학식",
    "식단",
    "학생식당",
    "샬롬관 식당",
    "오늘의 메뉴",
    "점심 메뉴",
    "저녁 메뉴",
)

NOTICE_INTENT_TERMS = (
    "공지",
    "안내",
    "모집",
    "채용",
    "신청 방법",
)

CALENDAR_TIME_TERMS = (
    "언제",
    "기간",
    "예정일",
    "시작일",
    "종료일",
    "며칠",
    "날짜",
    "일정",
    "학사일정",
)

ACADEMIC_CALENDAR_TERMS = (
    "개강",
    "수강신청",
    "수강정정",
    "수강변경",
    "수강철회",
    "수강포기",
    "중간고사",
    "중간시험",
    "기말고사",
    "기말시험",
    "강의평가",
    "계절수업",
    "계절학기",
    "방학",
    "휴일",
    "휴업일",
    "공휴일",
    "학위수여식",
    "졸업식",
)

CATEGORY_TERMS = (
    (
        "장학",
        (
            "장학",
            "학자금",
            "근로장학생",
            "등록금 감면",
        ),
    ),
    (
        "취창업",
        (
            "취업",
            "채용",
            "창업",
            "인턴",
            "현장실습",
            "직무",
        ),
    ),
    (
        "학습/상담",
        (
            "학습",
            "튜터링",
            "상담",
            "심리",
            "학습코칭",
        ),
    ),
    (
        "학사",
        (
            "학사",
            "수강",
            "전공",
            "휴학",
            "복학",
            "시험",
            "졸업",
            "학위",
            "성적",
            "등록",
        ),
    ),
)


def _contains_any(question: str, terms: tuple[str, ...]) -> bool:
    return any(term in question for term in terms)


def _extract_academic_year(question: str, today: date) -> int:
    match = re.search(r"(20\d{2})\s*년?", question)
    return int(match.group(1)) if match else today.year


def _extract_meal_date(question: str, today: date) -> date | None:
    full_date = re.search(
        r"(20\d{2})\s*(?:년|[-./])\s*(\d{1,2})\s*(?:월|[-./])\s*(\d{1,2})\s*일?",
        question,
    )
    if full_date:
        try:
            return date(*(int(value) for value in full_date.groups()))
        except ValueError:
            return None

    month_day = re.search(r"(?<!\d)(\d{1,2})\s*월\s*(\d{1,2})\s*일", question)
    if month_day:
        try:
            return date(today.year, int(month_day.group(1)), int(month_day.group(2)))
        except ValueError:
            return None

    if "모레" in question:
        return today + timedelta(days=2)
    if "내일" in question:
        return today + timedelta(days=1)
    if "어제" in question:
        return today - timedelta(days=1)
    if "오늘" in question:
        return today
    return None


def _notice_category(question: str) -> str | None:
    for category, terms in CATEGORY_TERMS:
        if _contains_any(question, terms):
            return category
    return None


def infer_retrieval_filter(
    question: str,
    *,
    today: date | None = None,
) -> RetrievalFilterDecision:
    """질문 의도가 충분히 명확할 때만 Qdrant 메타데이터 필터를 반환합니다."""
    normalized = " ".join(question.split())
    reference_date = today or date.today()

    if _contains_any(normalized, MEAL_TERMS):
        metadata_filter: dict[str, str | int] = {"source": "학식"}
        reasons = ["학식·식단 관련 고유어 감지"]
        meal_date = _extract_meal_date(normalized, reference_date)
        if meal_date:
            metadata_filter["date"] = meal_date.isoformat()
            reasons.append(f"식단 날짜 판별: {meal_date.isoformat()}")
        return RetrievalFilterDecision(
            metadata_filter=metadata_filter,
            confidence="high",
            reasons=tuple(reasons),
        )

    if _contains_any(normalized, SHUTTLE_TERMS):
        return RetrievalFilterDecision(
            metadata_filter={"source": "셔틀시간표"},
            confidence="high",
            reasons=("셔틀 운행 관련 고유어 감지",),
        )

    notice_intent = _contains_any(normalized, NOTICE_INTENT_TERMS)
    calendar_intent = _contains_any(normalized, ACADEMIC_CALENDAR_TERMS) and _contains_any(
        normalized, CALENDAR_TIME_TERMS
    )

    # '공지'와 '안내'처럼 문서 의도가 명시되면 학사 용어가 포함돼도 공지를 우선합니다.
    if notice_intent:
        metadata_filter: dict[str, str | int] = {"source": "공지사항"}
        category = _notice_category(normalized)
        reasons = ["공지·안내·모집 의도 감지"]
        if category:
            metadata_filter["category"] = category
            reasons.append(f"공지 범주 판별: {category}")
        return RetrievalFilterDecision(
            metadata_filter=metadata_filter,
            confidence="high",
            reasons=tuple(reasons),
        )

    if calendar_intent:
        academic_year = _extract_academic_year(normalized, reference_date)
        return RetrievalFilterDecision(
            metadata_filter={
                "source": "학사일정",
                "academic_year": academic_year,
            },
            confidence="high",
            reasons=("학사 행사와 날짜·기간 의도 동시 감지",),
        )

    return RetrievalFilterDecision(
        metadata_filter={},
        confidence="none",
        reasons=("하드 필터를 적용할 만큼 질문 의도가 명확하지 않음",),
    )

def build_qdrant_filter(metadata_filter: dict) -> Filter | None:
    if not metadata_filter:
        return None

    return Filter(
        must=[
            FieldCondition(
                key=f"metadata.{field}",
                match=MatchValue(value=value),
            )
            for field, value in metadata_filter.items()
        ]
    )
