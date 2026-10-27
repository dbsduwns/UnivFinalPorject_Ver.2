"""Upsert an academic-calendar JSON seed into the configured PostgreSQL database."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.database import SessionLocal  # noqa: E402
from app.models.academic_calendar_event import AcademicCalendarEvent  # noqa: E402


DEFAULT_SEED_PATH = BACKEND_DIR / "data" / "academic_calendar_seed.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="학사일정 seed를 PostgreSQL에 upsert합니다.")
    parser.add_argument("--seed-path", type=Path, default=DEFAULT_SEED_PATH)
    return parser.parse_args()


def load_seed(seed_path: Path) -> dict:
    payload = json.loads(seed_path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError("지원하지 않는 academic calendar seed 버전입니다.")
    if not isinstance(payload.get("academic_year"), int):
        raise ValueError("academic_year가 필요합니다.")
    if not isinstance(payload.get("events"), list) or not payload["events"]:
        raise ValueError("events는 비어 있지 않은 배열이어야 합니다.")
    source = payload.get("source_document")
    if not isinstance(source, dict) or not source.get("filename") or not source.get("sha256"):
        raise ValueError("source_document filename과 sha256이 필요합니다.")
    return payload


def upsert_seed(db, payload: dict) -> tuple[int, int]:
    academic_year = payload["academic_year"]
    source = payload["source_document"]
    existing = {
        (event.title, event.start_date, event.end_date): event
        for event in db.query(AcademicCalendarEvent)
        .filter(AcademicCalendarEvent.academic_year == academic_year)
        .all()
    }

    # A new revision is authoritative for its entire academic year. Existing
    # rows are retained for auditability but hidden unless present in this seed.
    db.query(AcademicCalendarEvent).filter(
        AcademicCalendarEvent.academic_year == academic_year
    ).update({AcademicCalendarEvent.is_active: False}, synchronize_session="fetch")

    inserted = 0
    updated = 0
    for item in payload["events"]:
        title = str(item.get("title") or "").strip()
        if not title:
            raise ValueError("이벤트 title은 비어 있을 수 없습니다.")
        start_date = date.fromisoformat(str(item["start_date"]))
        end_date = date.fromisoformat(str(item["end_date"]))
        if end_date < start_date:
            raise ValueError(f"종료일이 시작일보다 빠릅니다: {title}")

        key = (title, start_date, end_date)
        event = existing.get(key)
        if event is None:
            event = AcademicCalendarEvent(
                academic_year=academic_year,
                title=title,
                start_date=start_date,
                end_date=end_date,
            )
            db.add(event)
            inserted += 1
        else:
            updated += 1

        event.source_document = str(source["filename"])
        event.source_sha256 = str(source["sha256"])
        event.source_page = int(item["source_page"])
        event.is_active = True

    return inserted, updated


def main() -> None:
    args = parse_args()
    payload = load_seed(args.seed_path)
    db = SessionLocal()
    try:
        database_url = str(db.get_bind().url)
        parsed_url = urlparse(database_url)
        target = f"{parsed_url.scheme}://{parsed_url.hostname or 'unknown'}/{parsed_url.path.lstrip('/') or 'unknown'}"
        print(f"DB 적재 대상: {target}")
        inserted, updated = upsert_seed(db, payload)
        db.commit()
        active_count = db.query(AcademicCalendarEvent).filter(
            AcademicCalendarEvent.academic_year == payload["academic_year"],
            AcademicCalendarEvent.is_active.is_(True),
        ).count()
        print(f"학사일정 seed 완료: 신규 {inserted}개, 갱신 {updated}개, 활성 {active_count}개")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
