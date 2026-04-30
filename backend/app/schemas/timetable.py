from datetime import datetime, time

from pydantic import BaseModel


class TimetableCreate(BaseModel):
    name: str
    semester: str
    is_main: bool = False

class TimetableUpdate(BaseModel):
    name: str | None = None
    semester: str | None = None
    is_main: bool |None = None

class TimetableResponse(BaseModel):
    id: int
    user_id: int
    name: str
    semester: str
    is_main: bool
    share_token: str | None = None
    created_at: datetime | None = None

    model_config = {
        "from_attributes": True
    }

class TimetableCourseCreate(BaseModel):
    course_id: int
    color: str = "#3B82F6"


class TimetableCourseResponse(BaseModel):
    id: int
    timetable_id: int
    course_id: int
    color: str
    created_at: datetime | None = None

    model_config = {
        "from_attributes": True
    }


class CourseScheduleResponse(BaseModel):
    id: int
    course_id: int
    day_of_week: str
    start_time: time
    end_time: time

    model_config = {
        "from_attributes": True
    }


class CourseDetailResponse(BaseModel):
    id: int
    subject_id: int
    subject_code: str | None = None
    name: str | None = None
    credits: int | None = None
    section: str
    professor: str | None = None
    color: str | None = None
    schedules: list[CourseScheduleResponse] = []

    model_config = {
        "from_attributes": True
    }


class CustomScheduleCreate(BaseModel):
    name: str
    day_of_week: str
    start_time: time
    end_time: time
    color: str = "#3B82F6"
    memo: str | None = None

class CustomScheduleUpdate(BaseModel):
    name: str | None = None
    day_of_week: str | None = None
    start_time: time | None = None
    end_time: time | None = None
    color: str | None = None
    memo: str | None = None

class CustomScheduleResponse(BaseModel):
    id: int
    timetable_id: int
    name: str
    day_of_week: str
    start_time: time
    end_time: time
    color: str
    memo: str | None = None

    model_config = {
        "from_attributes": True
    }


class TimetableDetailResponse(TimetableResponse):
    courses: list[CourseDetailResponse] = []
    custom_schedules: list[CustomScheduleResponse] = []
    total_credits: int = 0