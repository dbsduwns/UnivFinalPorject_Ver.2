from app.services.ai_fallback import build_ai_fallback_reply


def test_fallback_covers_exhibition_questions():
    assert "학사일정 메뉴" in build_ai_fallback_reply("이번달 학사일정 알려줘")
    assert "공지사항 메뉴" in build_ai_fallback_reply("최근 취업 공지 알려줘")
    assert "시간표 메뉴" in build_ai_fallback_reply("오늘 수업 일정이 어떻게 되지?")
    assert "식단 메뉴" in build_ai_fallback_reply("오늘 학식 메뉴 알려줘")
    assert "셔틀 메뉴" in build_ai_fallback_reply("셔틀버스 시간표 알려줘")


def test_fallback_has_generic_exhibition_reply():
    reply = build_ai_fallback_reply("캠퍼스 앱은 무엇을 할 수 있어?")

    assert "각 메뉴에서 직접 확인" in reply
