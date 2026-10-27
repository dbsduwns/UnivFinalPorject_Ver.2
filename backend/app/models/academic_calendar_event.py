from sqlalchemy import Boolean, Column, Date, Integer, String, TIMESTAMP, UniqueConstraint
from sqlalchemy.sql import func

from app.database import Base


class AcademicCalendarEvent(Base):
    """A versioned, queryable academic-calendar event from an official source."""

    __tablename__ = "academic_calendar_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    academic_year = Column(Integer, nullable=False, index=True)
    title = Column(String(500), nullable=False)
    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=False, index=True)
    source_document = Column(String(255), nullable=False)
    source_sha256 = Column(String(64), nullable=False)
    source_page = Column(Integer, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint(
            "academic_year",
            "title",
            "start_date",
            "end_date",
            name="uq_academic_calendar_event_dates",
        ),
    )
