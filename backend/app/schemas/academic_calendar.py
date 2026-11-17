from datetime import date

from pydantic import BaseModel


class AcademicCalendarEventResponse(BaseModel):
    title: str
    start_date: date
    end_date: date


class AcademicCalendarMonthResponse(BaseModel):
    year: int
    month: int
    events: list[AcademicCalendarEventResponse]
