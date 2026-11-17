from calendar import monthrange
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.academic_calendar_event import AcademicCalendarEvent
from app.schemas.academic_calendar import (
    AcademicCalendarEventResponse,
    AcademicCalendarMonthResponse,
)
from app.services.academic_calendar import ACADEMIC_CALENDAR


router = APIRouter(prefix="/api/academic-calendar", tags=["academic-calendar"])


@router.get("/", response_model=AcademicCalendarMonthResponse)
def get_academic_calendar(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
):
    """Return active academic events overlapping the requested month."""
    month_start = date(year, month, 1)
    month_end = date(year, month, monthrange(year, month)[1])

    rows = (
        db.query(AcademicCalendarEvent)
        .filter(
            AcademicCalendarEvent.is_active.is_(True),
            AcademicCalendarEvent.start_date <= month_end,
            AcademicCalendarEvent.end_date >= month_start,
        )
        .order_by(
            AcademicCalendarEvent.start_date,
            AcademicCalendarEvent.end_date,
            AcademicCalendarEvent.title,
        )
        .all()
    )

    # Keep the app useful during a first deployment before the seed table is populated.
    events = rows or [
        event
        for event in ACADEMIC_CALENDAR
        if event.start <= month_end and event.end >= month_start
    ]

    return AcademicCalendarMonthResponse(
        year=year,
        month=month,
        events=[
            AcademicCalendarEventResponse(
                title=event.title,
                start_date=event.start_date if hasattr(event, "start_date") else event.start,
                end_date=event.end_date if hasattr(event, "end_date") else event.end,
            )
            for event in events
        ],
    )
