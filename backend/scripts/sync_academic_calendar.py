from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")
# Never overwrite variables injected by Cloud Run/Secret Manager. The local
# file is only a fallback for developer machines.
load_dotenv(BACKEND_DIR / ".env.cloudrun")

from langchain_core.documents import Document  # noqa: E402

from app.core.ai_providers import build_embeddings  # noqa: E402
from app.core.vector_store import QdrantDocumentStore  # noqa: E402
from app.crawlers.academic_calendar_crawler import (  # noqa: E402
    ACADEMIC_CALENDAR_URL,
    CrawledAcademicCalendarEvent,
    crawl_academic_calendar,
    parse_academic_calendar_file,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crawl the official undergraduate calendar and synchronize it to Qdrant."
    )
    parser.add_argument("--year", type=int, help="Fallback year used while parsing date rows")
    parser.add_argument(
        "--url",
        default=os.getenv("ACADEMIC_CALENDAR_URL", ACADEMIC_CALENDAR_URL),
    )
    parser.add_argument(
        "--html-file",
        help="Parse a saved HTML file instead of opening the official website",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print parsed events without writing to Qdrant",
    )
    return parser.parse_args()


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} environment variable is required")
    return value


def build_document(event: CrawledAcademicCalendarEvent) -> Document:
    crawled_at = datetime.now(timezone.utc).isoformat()
    content = (
        f"학사일정: {event.title}\n"
        f"시작일: {event.start.isoformat()}\n"
        f"종료일: {event.end.isoformat()}\n"
        f"기간: {event.date_text}\n"
        "대상: 강남대학교 학부"
    )
    return Document(
        page_content=content,
        metadata={
            "source": "학사일정",
            "source_type": "undergraduate_academic_calendar",
            "title": event.title,
            "event": event.title,
            "date": event.date_text,
            "start_date": event.start.isoformat(),
            "end_date": event.end.isoformat(),
            "academic_year": event.calendar_year,
            "source_url": event.source_url,
            "crawled_at": crawled_at,
        },
    )


def main() -> None:
    args = parse_args()
    if args.html_file:
        events = parse_academic_calendar_file(args.html_file, default_year=args.year)
    else:
        events = crawl_academic_calendar(
            url=args.url,
            default_year=args.year,
        )

    if not events:
        raise RuntimeError("동기화할 학사일정이 없습니다.")

    print(f"학사일정 {len(events)}개를 수집했습니다.", flush=True)
    for event in events:
        print(f"- {event.date_text}: {event.title}", flush=True)

    if args.dry_run:
        print("dry-run이므로 Qdrant에는 저장하지 않았습니다.", flush=True)
        return

    embedding_provider = os.getenv("EMBEDDING_PROVIDER", "cloudflare").lower()
    print(
        "환경변수 주입 상태: "
        f"CLOUDFLARE_API_TOKEN={'설정됨' if os.getenv('CLOUDFLARE_API_TOKEN') else '누락'}, "
        f"CLOUDFLARE_ACCOUNT_ID={'설정됨' if os.getenv('CLOUDFLARE_ACCOUNT_ID') else '누락'}, "
        f"QDRANT_API_KEY={'설정됨' if os.getenv('QDRANT_API_KEY') else '누락'}, "
        f"QDRANT_URL={'설정됨' if os.getenv('QDRANT_URL') else '누락'}",
        flush=True,
    )
    store = QdrantDocumentStore(
        url=require_env("QDRANT_URL"),
        api_key=require_env("QDRANT_API_KEY"),
        collection_name=os.getenv("QDRANT_COLLECTION", "knu-campus-bge-m3"),
        embeddings=build_embeddings(embedding_provider),
    )
    documents = [build_document(event) for event in events]
    ids = [event.stable_id for event in events]
    removed_count = store.replace_documents_by_source(
        documents,
        ids=ids,
        source="학사일정",
    )
    print(
        f"Qdrant 동기화 완료: {len(documents)}개 upsert, "
        f"이전 일정 {removed_count}개 삭제",
        flush=True,
    )


if __name__ == "__main__":
    main()
