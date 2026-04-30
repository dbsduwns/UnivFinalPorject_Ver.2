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


class DepartmentCrawlTarget(BaseModel):
    code: str
    name: str
    course_type: str | None = None


class DepartmentCourseCrawlRequest(BaseModel):
    session_cookie: str
    year: str
    semester: str
    student_number: str
    student_grade: str = "4"
    student_department_code: str
    fact_code: str
    fact_srch: str
    student_dorn: str = "1"
    grad_srch: str | None = None
    dept_code2: str = "5100"
    grad_area1: str = "H4"
    grad_area2: str = "H4"
    delay_seconds: float = 1.0
    save: bool = True
    departments: list[DepartmentCrawlTarget]


class DepartmentCourseCrawlResult(BaseModel):
    department_code: str
    department_name: str
    parsed_count: int
    saved_count: int
    error: str | None = None


class DepartmentCourseCrawlResponse(BaseModel):
    department_count: int
    parsed_count: int
    saved_count: int
    results: list[DepartmentCourseCrawlResult]


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
