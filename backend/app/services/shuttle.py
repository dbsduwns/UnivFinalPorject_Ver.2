from sqlalchemy.orm import Session
from app.models.shuttle import Shuttle
from app.core.notification import notify_users_by_type_sync


def get_shuttle_schedules(db: Session, semester: str | None = None) -> list[Shuttle]:
    query = db.query(Shuttle)

    if semester:
        query = query.filter(Shuttle.semester == semester)

    return query.order_by(Shuttle.id.desc()).all()


def get_latest_shuttle_schedule(db: Session) -> Shuttle | None:
    return db.query(Shuttle).order_by(Shuttle.id.desc()).first()


def crawl_and_save_shuttle_schedule(db: Session) -> Shuttle:
    from app.crawlers.shuttle_crawler import crawl_shuttle_schedule

    item = crawl_shuttle_schedule()

    existing = (
        db.query(Shuttle)
        .filter(Shuttle.file_url == item["file_url"])
        .first()
    )

    if existing:
        changed = any(
            getattr(existing, field) != item[field]
            for field in ("title", "semester", "source_url", "original_filename")
        )
        existing.title = item["title"]
        existing.source_url = item["source_url"]
        existing.semester = item["semester"]
        existing.original_filename = item["original_filename"]
        db.commit()
        db.refresh(existing)
        if changed:
            notify_users_by_type_sync(
                db,
                "shuttle_alert",
                "🚌 셔틀버스 크롤링 업데이트",
                f"[{item['semester']}] 시간표 파일이 갱신되었습니다.",
                {
                    "type": "shuttle",
                    "semester": item["semester"],
                },
            )
        return existing

    schedule = Shuttle(**item)
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    notify_users_by_type_sync(
        db,
        "shuttle_alert",
        "🚌 셔틀버스 크롤링 업데이트",
        f"[{item['semester']}] 새로운 셔틀버스 시간표가 등록되었습니다.",
        {
            "type": "shuttle",
            "semester": item["semester"],
        },
    )
    return schedule
