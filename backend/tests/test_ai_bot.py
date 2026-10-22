from types import SimpleNamespace

import app.core.ai_bot as ai_bot_module
from app.core.ai_bot import CampusAIBot, DEFAULT_QDRANT_COLLECTION


class FakeRetriever:
    def __init__(self, documents):
        self.documents = documents
        self.queries = []

    async def ainvoke(self, query):
        self.queries.append(query)
        return self.documents


def _bot_with_retriever(documents):
    bot = object.__new__(CampusAIBot)
    bot.retriever = FakeRetriever(documents)
    return bot


def _run_immediate(coroutine):
    """실제 I/O가 없는 테스트 코루틴을 Windows 이벤트 루프 없이 실행한다."""
    try:
        coroutine.send(None)
    except StopIteration as exc:
        return exc.value
    raise AssertionError("테스트 코루틴이 예상과 달리 실제 I/O를 대기했습니다.")


def test_default_qdrant_collection_matches_cloudflare_sync_collection():
    assert DEFAULT_QDRANT_COLLECTION == "knu-campus-bge-m3"


def test_academic_qdrant_document_is_used_without_static_fallback(monkeypatch):
    calendar_document = SimpleNamespace(
        page_content="학사일정: 2학기 중간시험 기간",
        metadata={
            "source": "학사일정",
            "title": "2학기 중간시험 기간",
            "start_date": "2026-10-20",
            "end_date": "2026-10-26",
        },
    )
    bot = _bot_with_retriever([calendar_document])

    def fail_if_called(_question):
        raise AssertionError("Qdrant 학사일정이 있으면 정적 fallback을 사용하면 안 됩니다.")

    monkeypatch.setattr(
        ai_bot_module,
        "build_academic_calendar_context",
        fail_if_called,
    )

    context = _run_immediate(bot.build_context("중간시험 일정 알려줘"))

    assert "[Qdrant 검색 문서]" in context
    assert "2학기 중간시험 기간" in context


def test_static_calendar_is_fallback_when_qdrant_has_no_calendar(monkeypatch):
    notice_document = SimpleNamespace(
        page_content="장학 공지",
        metadata={"source": "공지사항", "title": "장학 공지"},
    )
    bot = _bot_with_retriever([notice_document])
    monkeypatch.setattr(
        ai_bot_module,
        "build_academic_calendar_context",
        lambda _question: "[구조화된 학사일정]\n- fallback 일정",
    )

    context = _run_immediate(bot.build_context("다음 학사일정 알려줘"))

    assert "장학 공지" in context
    assert "fallback 일정" in context


def test_original_question_is_preserved_in_qdrant_search_query():
    bot = _bot_with_retriever([])

    _run_immediate(
        bot.build_context(
            "국가장학금 공지 알려줘",
            "강남대학교 국가장학금 신청 공지사항",
        )
    )

    query = bot.retriever.queries[0]
    assert "국가장학금 공지 알려줘" in query
    assert "강남대학교 국가장학금 신청 공지사항" in query


def test_timetable_only_context_skips_qdrant_search():
    bot = _bot_with_retriever([])
    personal_context = "[사용자 개인 시간표]\n- 월요일 09:00~10:00 자료구조"

    context = _run_immediate(
        bot.build_context(
            "오늘 내 시간표에서 첫 수업이 뭐야?",
            personal_context=personal_context,
        )
    )

    assert personal_context in context
    assert bot.retriever.queries == []


def test_timetable_question_with_shuttle_still_uses_qdrant():
    bot = _bot_with_retriever([])

    _run_immediate(
        bot.build_context(
            "내 수업 끝나고 셔틀 탈 수 있어?",
            personal_context="[사용자 개인 시간표]",
        )
    )

    assert len(bot.retriever.queries) == 1


def test_query_rewrite_is_skipped_for_clear_questions_and_used_for_followups():
    assert not CampusAIBot._needs_query_rewrite("오늘 내 첫 수업이 뭐야?")
    assert CampusAIBot._needs_query_rewrite("그럼 몇 시야?")
    assert CampusAIBot._needs_query_rewrite("언제야?")


def test_add_documents_raises_when_vector_store_is_unavailable(monkeypatch):
    bot = object.__new__(CampusAIBot)
    bot.indexing_ready = False
    bot.vectorstore = None
    monkeypatch.setattr(bot, "initialize", lambda: False)

    document = SimpleNamespace(page_content="공지", metadata={})

    try:
        bot.add_documents([document])
    except RuntimeError as exc:
        assert "벡터 DB가 준비되지 않아" in str(exc)
    else:
        raise AssertionError("벡터 DB가 없으면 저장 성공처럼 처리하면 안 됩니다.")
