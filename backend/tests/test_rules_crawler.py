from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.crawlers.rules_crawler import (
    SAFETY_LIMIT_BYTES,
    RuleTarget,
    check_database_capacity,
    parse_articles,
    parse_targets,
)
from app.core import ai_bot as ai_bot_module
from app.models.regulation_article import RegulationArticle
from app.services.regulations import build_regulation_context_from_db, is_regulation_query


def test_public_rule_page_parses_article_and_graduation_context(monkeypatch):
    list_html = """<tr onclick="movepageNew('true','8','2,1,1')">
        <td>강남대학교학칙</td></tr>"""
    target = parse_targets(list_html)[0]
    assert target == RuleTarget("강남대학교학칙", "2", "1", "1")

    detail_html = """<tr id="row7"><td>제7조 (졸업) 졸업에 필요한 요건을 정한다.</td></tr>"""
    article = parse_articles(detail_html, target)[0]
    engine = create_engine("sqlite://")
    RegulationArticle.__table__.create(engine)
    with Session(engine) as db:
        db.add(RegulationArticle(
            source_key=article.source_key,
            rule_title=article.rule_title,
            article_heading=article.article_heading,
            content=article.content,
            content_hash=article.content_hash,
            source_url="https://example.com/rules",
            synced_at=datetime(2026, 11, 2, tzinfo=timezone.utc),
        ))
        db.commit()
        context = build_regulation_context_from_db(db, "졸업에 관한 학칙 알려줘")
    monkeypatch.setattr(ai_bot_module, "SessionLocal", lambda: Session(engine))

    async def no_documents(_question, _rewritten):
        return []

    monkeypatch.setattr(ai_bot_module.campus_ai_bot, "_retrieve_documents", no_documents)
    coroutine = ai_bot_module.campus_ai_bot.build_context("졸업에 관한 학칙 알려줘")
    try:
        coroutine.send(None)
    except StopIteration as result:
        chatbot_context = result.value
    else:
        raise AssertionError("build_context unexpectedly awaited an external service")
    assert "제7조" in context
    assert "졸업에 필요한 요건" in context
    assert "제7조" in chatbot_context
    assert "학사일정" not in chatbot_context
    assert is_regulation_query("졸업에 관한 학칙 알려줘")


def test_capacity_check_stops_before_free_tier_limit():
    class Scalar:
        def scalar_one(self):
            return SAFETY_LIMIT_BYTES - 100

    class Database:
        def execute(self, _query):
            return Scalar()

    try:
        check_database_capacity(Database(), 100)
    except RuntimeError as exc:
        assert "적재 중단" in str(exc)
    else:
        raise AssertionError("capacity check allowed an over-limit write")
