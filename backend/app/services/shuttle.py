from sqlalchemy.orm import Session
from app.models.shuttle import Shuttle
from app.crawlers.shuttle_crawler import crawl_shuttle_schedule


def get_shuttle_schedules(db: Session, semester: str | None = None) -> list[Shuttle]:
    query = db.query(Shuttle)

    if semester:
        query = query.filter(Shuttle.semester == semester)

    return query.order_by(Shuttle.id.desc()).all()


def get_latest_shuttle_schedule(db: Session) -> Shuttle | None:
    return db.query(Shuttle).order_by(Shuttle.id.desc()).first()


def crawl_and_save_shuttle_schedule(db: Session) -> Shuttle:
    item = crawl_shuttle_schedule()

    existing = (
        db.query(Shuttle)
        .filter(Shuttle.file_url == item["file_url"])
        .first()
    )

    if existing:
        existing.title = item["title"]
        existing.source_url = item["source_url"]
        existing.semester = item["semester"]
        existing.original_filename = item["original_filename"]
        db.commit()
        db.refresh(existing)
        return existing

    schedule = Shuttle(**item)
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule
