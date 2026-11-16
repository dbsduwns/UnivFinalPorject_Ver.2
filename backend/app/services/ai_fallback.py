"""Deterministic exhibition replies used when the AI provider is unavailable."""

_FALLBACK_PREFIX = "AI 연결이 원활하지 않습니다. 잠시 후 다시 시도해주세요.\n\n"


def build_ai_fallback_reply(question: str) -> str:
    """Return a safe, deterministic reply for the exhibition's core questions."""
    normalized = question.strip().lower()

    if "학사일정" in normalized or "학사 일정" in normalized:
        return (
            _FALLBACK_PREFIX +
            "학사일정은 앱의 학사일정 메뉴에서 확인할 수 있습니다. "
            "전시용 데이터에는 이번 학기 주요 학사일정이 미리 등록되어 있습니다."
        )

    if "취업" in normalized or "공지" in normalized:
        return (
            _FALLBACK_PREFIX +
            "취업 및 학교 공지는 공지사항 메뉴에서 최신 목록과 상세 내용을 확인할 수 있습니다."
        )

    if "오늘" in normalized and ("수업" in normalized or "시간표" in normalized):
        return (
            _FALLBACK_PREFIX +
            "오늘 수업 일정은 시간표 메뉴에서 확인할 수 있습니다. "
            "로그인한 계정의 전시용 시간표가 표시됩니다."
        )

    if "학식" in normalized or "식단" in normalized or "메뉴" in normalized:
        return (
            _FALLBACK_PREFIX +
            "오늘의 학식 메뉴는 식단 메뉴에서 확인할 수 있습니다."
        )

    if "셔틀" in normalized or "버스" in normalized:
        return (
            _FALLBACK_PREFIX +
            "셔틀버스 운행 정보는 셔틀 메뉴에서 학기별 시간표와 노선을 확인할 수 있습니다."
        )

    return (
        _FALLBACK_PREFIX +
        "학사일정, 공지사항, 오늘 수업, 학식, 셔틀버스와 관련된 질문은 "
        "각 메뉴에서 직접 확인할 수 있습니다."
    )
