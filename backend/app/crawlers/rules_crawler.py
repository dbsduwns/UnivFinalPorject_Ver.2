"""Crawl public university regulations into the configured PostgreSQL database.

Cloud Run Job command: ``python -m app.crawlers.rules_crawler``.
"""

from __future__ import annotations

import argparse
import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from sqlalchemy import text

from app.database import SessionLocal
from app.models.regulation_article import RegulationArticle


load_dotenv(Path(__file__).resolve().parents[2] / ".env")
LIST_URL = "https://app.kangnam.ac.kr/knumis/mo_open/rulesL1.jsp?rglt_cont2=&rglt_cont=&gubn=&save_gubn="
DETAIL_URL = "https://app.kangnam.ac.kr/knumis/mo_open/rulesL2.jsp"
FREE_DATABASE_BYTES = 500_000_000
SAFETY_LIMIT_BYTES = 450_000_000


@dataclass(frozen=True)
class RuleTarget:
    title: str
    pyon: str
    jang: str
    bnho: str

    @property
    def key(self) -> str:
        return f"{self.pyon}:{self.jang}:{self.bnho}"


@dataclass(frozen=True)
class Article:
    source_key: str
    rule_title: str
    article_heading: str
    content: str
    content_hash: str


def should_crawl(name: str, pyon: str, jang: str) -> bool:
    return (
        (pyon == "2" and jang == "1")
        or pyon == "4"
        or (pyon == "5" and jang in {"1", "2"})
        or pyon == "6"
        or (pyon == "3" and jang == "5" and any(
            word in name for word in ("안전", "개인정보", "이동장치")
        ))
    )


def parse_targets(html: str) -> list[RuleTarget]:
    targets: list[RuleTarget] = []
    seen: set[str] = set()
    for row in BeautifulSoup(html, "html.parser").select("tr[onclick]"):
        match = re.fullmatch(
            r"\s*movepageNew\('[^']+','[^']+','(\d+),(\d+),(\d+)'\)\s*;?\s*",
            row.get("onclick", ""),
        )
        if not match:
            continue
        pyon, jang, bnho = match.groups()
        title = " ".join(row.get_text(" ", strip=True).split())
        target = RuleTarget(title, pyon, jang, bnho)
        if should_crawl(title, pyon, jang) and target.key not in seen:
            targets.append(target)
            seen.add(target.key)
    return targets


def parse_articles(html: str, target: RuleTarget) -> list[Article]:
    articles: list[Article] = []
    for row in BeautifulSoup(html, "html.parser").select('tr[id^="row"]'):
        row_id = row.get("id", "")
        if not re.fullmatch(r"row\d+", row_id):
            continue
        content = " ".join(row.get_text(" ", strip=True).split())
        heading = re.match(r"제\s*\d+\s*조(?:의\s*\d+)?(?:\s*\([^)]*\))?", content)
        if not heading or len(content) < 12:
            continue
        articles.append(Article(
            source_key=f"{target.key}:{row_id}",
            rule_title=target.title,
            article_heading=heading.group().strip(),
            content=content,
            content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
        ))
    return articles


def crawl_rules(*, max_rules: int | None = None) -> tuple[list[Article], int]:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(LIST_URL, wait_until="networkidle", timeout=60_000)
            targets = parse_targets(page.content())
            if not targets or not any(target.key == "2:1:1" for target in targets):
                raise RuntimeError("공식 규정 목록에서 강남대학교학칙을 찾지 못했습니다.")
            targets = targets[:max_rules] if max_rules is not None else targets
            articles: list[Article] = []
            for target in targets:
                response = page.request.post(DETAIL_URL, form={
                    "rglt_pyon": target.pyon,
                    "rglt_jang": target.jang,
                    "rglt_bnho": target.bnho,
                    "rglt_cont": "",
                    "rglt_alls": "Y",
                    "save_gubn": "2",
                    "gubn": "",
                }, timeout=60_000)
                if not response.ok:
                    raise RuntimeError(f"규정 본문 요청 실패: {target.title}, HTTP {response.status}")
                rule_articles = parse_articles(
                    response.body().decode("cp949"), target
                )
                if not rule_articles:
                    raise RuntimeError(f"규정 조항을 찾지 못했습니다: {target.title}")
                articles.extend(rule_articles)
            return articles, len(targets)
        finally:
            browser.close()


def estimated_storage_bytes(articles: list[Article]) -> int:
    # Four times the UTF-8 payload allows for row and index overhead.
    return 4 * sum(
        len(article.content.encode("utf-8"))
        + len(article.rule_title.encode("utf-8"))
        + len(article.article_heading.encode("utf-8"))
        + 512
        for article in articles
    )


def check_database_capacity(db, estimated_bytes: int) -> int:
    current = int(db.execute(text("SELECT pg_database_size(current_database())")).scalar_one())
    if current + estimated_bytes >= SAFETY_LIMIT_BYTES:
        raise RuntimeError(
            f"Supabase 무료 DB 용량 안전선 초과 예상: {current:,}B + "
            f"{estimated_bytes:,}B >= {SAFETY_LIMIT_BYTES:,}B. 적재 중단."
        )
    return current


def upsert_articles(articles: list[Article]) -> tuple[int, int]:
    db = SessionLocal()
    try:
        before = check_database_capacity(db, estimated_storage_bytes(articles))
        existing = {
            row.source_key: row
            for row in db.query(RegulationArticle).filter(
                RegulationArticle.source_key.in_([a.source_key for a in articles])
            )
        }
        inserted = updated = 0
        now = datetime.now(timezone.utc)
        for article in articles:
            row = existing.get(article.source_key)
            if row is None:
                row = RegulationArticle(source_key=article.source_key)
                db.add(row)
                inserted += 1
            elif row.content_hash != article.content_hash:
                updated += 1
            row.rule_title = article.rule_title
            row.article_heading = article.article_heading
            row.content = article.content
            row.content_hash = article.content_hash
            row.source_url = LIST_URL
            row.synced_at = now
        db.flush()
        after = int(db.execute(text("SELECT pg_database_size(current_database())")).scalar_one())
        if after >= SAFETY_LIMIT_BYTES:
            raise RuntimeError("Supabase 무료 DB 용량 안전선에 도달해 적재를 취소했습니다.")
        db.commit()
        print(f"DB 사용량: {before:,}B → {after:,}B (안전선 {SAFETY_LIMIT_BYTES:,}B)")
        return inserted, updated
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="공식 학칙을 Supabase PostgreSQL에 적재")
    parser.add_argument("--dry-run", action="store_true", help="수집·용량 확인만 수행")
    parser.add_argument("--max-rules", type=int, help="수집할 규정 수 제한")
    args = parser.parse_args()
    if args.max_rules is not None and args.max_rules < 1:
        parser.error("--max-rules는 1 이상이어야 합니다.")
    articles, rule_count = crawl_rules(max_rules=args.max_rules)
    estimated = estimated_storage_bytes(articles)
    with SessionLocal() as db:
        current = check_database_capacity(db, estimated)
    print(
        f"수집: 규정 {rule_count}개, 조항 {len(articles)}개, "
        f"DB 사용량 {current:,}B, 보수적 추가 예상 {estimated:,}B"
    )
    if args.dry_run:
        print("dry-run: DB에 저장하지 않았습니다.")
        return
    inserted, updated = upsert_articles(articles)
    print(f"학칙 적재 완료: 신규 {inserted}개, 변경 {updated}개")


if __name__ == "__main__":
    main()
