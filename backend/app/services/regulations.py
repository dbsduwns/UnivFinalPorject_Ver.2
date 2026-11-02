"""Select relevant official regulation articles from PostgreSQL for AI context."""

from __future__ import annotations

import re

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.regulation_article import RegulationArticle


RULE_WORDS = ("학칙", "규정", "졸업 요건", "졸업 기준", "졸업 학점", "졸업학점")
STOPWORDS = {"학칙", "규정", "관한", "관련", "내용", "알려줘", "알려주세요", "강남대학교"}


def is_regulation_query(question: str) -> bool:
    return any(word in question for word in RULE_WORDS)


def search_terms(question: str) -> list[str]:
    terms: list[str] = []
    for word in re.findall(r"[0-9A-Za-z가-힣]+", question):
        for suffix in ("에", "의", "을", "를", "은", "는", "이", "가"):
            if word.endswith(suffix) and len(word) > len(suffix) + 1:
                word = word[: -len(suffix)]
                break
        if len(word) > 1 and word not in STOPWORDS and word not in terms:
            terms.append(word)
    return terms[:5]


def build_regulation_context_from_db(db: Session, question: str, *, limit: int = 8) -> str:
    if not is_regulation_query(question):
        return ""
    terms = search_terms(question)
    query = db.query(RegulationArticle)
    if terms:
        conditions = [
            condition
            for term in terms
            for condition in (
                RegulationArticle.content.ilike(f"%{term}%"),
                RegulationArticle.rule_title.ilike(f"%{term}%"),
            )
        ]
        query = query.filter(or_(*conditions))
    else:
        query = query.filter(RegulationArticle.rule_title.ilike("%학칙%"))

    candidates = query.limit(500).all()

    def score(article: RegulationArticle) -> int:
        value = 3 if "학칙" in article.rule_title else 0
        for term in terms:
            value += 12 * (term in article.article_heading)
            value += 6 * (term in article.rule_title)
            value += 4 * (term in article.content)
        return value

    candidates.sort(key=lambda article: (-score(article), article.source_key))
    if not candidates:
        return ""
    lines = ["[Supabase 공식 학칙·규정]", "각 조항은 공식 규정 사이트의 본문입니다."]
    for article in candidates[:limit]:
        content = article.content
        if len(content) > 1800:
            positions = [content.find(term) for term in terms if content.find(term) >= 0]
            start = max(0, min(positions) - 120) if positions else 0
            content = ("…" if start else "") + content[start : start + 1800] + "…"
        lines.append(
            f"- {article.rule_title} {article.article_heading}\n"
            f"  {content}\n"
            f"  원문: {article.source_url}"
        )
    return "\n".join(lines)
