from datetime import datetime, time

from pydantic import BaseModel


class CourseImportRequest(BaseModel):
    html: str
    department: str | None = None
    save: bool = True


class ParsedCourseSchedule(BaseModel):
    day_of_week: str
    start_time: time
    end_time: time


class ParsedCourseResponse(BaseModel):
    subject_code: str
    section: str
    name: str
    professor: str | None = None
    credits: int
    hours: int
    schedule_text: str
    semester: str
    department: str | None = None
    schedules: list[ParsedCourseSchedule] = []


class CourseImportResponse(BaseModel):
    parsed_count: int
    saved_count: int
    items: list[ParsedCourseResponse]


class SubjectResponse(BaseModel):
    id: int
    name: str
    subject_code: str
    department: str | None = None
    credits: int
    course_type: str | None = None
    semester: str
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


class CourseResponse(BaseModel):
    id: int
    subject_id: int
    section: str
    professor: str | None = None
    max_students: int | None = None
    current_students: int | None = None
    created_at: datetime | None = None
    subject: SubjectResponse | None = None
    schedules: list[CourseScheduleResponse] = []

    model_config = {
        "from_attributes": True
    }
