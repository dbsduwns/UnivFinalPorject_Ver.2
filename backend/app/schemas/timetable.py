from pydantic import BaseModel
from datetime import datetime, date
from time import time

class TimetableCreate(BaseModel):
    name: str
    semester: str
    is_main: bool = False

class TimetableResponse(BaseModel):
    id: int
    user_id: int
    name: str
    semester: str
    is_main: bool
    created_at: datetime

    class Config:
        from_attributes = True

class TimetableDetailResponse(BaseModel):
    id: int
    user_id: int
    name: str
    semester: str
    is_main: bool
    share_token: str | None = None
    courses = list["CourseDetailResponse"] = []
    custom_schedules: list["CustomScheduleResponse"] = []
    total_credits: int = 0 

class TimetableCourseCreate(BaseModel):
    timetable_id: int
    course_id: int
    color: str = "#3B82F6"

class TimetableCourseResponse(BaseModel):
    id: int
    timetable_id: int
    course_id: int
    color: str
    created_at: datetime

    class Config:
        from_attributes = True

class WizardSelectionCreate(BaseModel):
    subject_id: int
    semester: str

class WizardSelectionResponse(BaseModel):
    id: int
    user_id: int
    semester: str
    subject_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class WizardResultResponse(BaseModel):
    combinations: list[wizardCombination]

class SubjectCreate(BaseModel):
    name: str
    subject_code: str
    department: str | None = None
    credits: int
    course_type: str | None = None
    semester: str

class SubjectResponse(BaseModel):
    id: int
    name: str
    subject_code: str
    department: str | None = None
    credits: int
    course_type: str | None= None
    semester: str
    created_at: datetime

    class Config:
        from_attributes = True

class CourseCreate(BaseModel):
    subject_id: int
    section: str
    professor: str | None = None
    room_id: int | None = None
    max_students: int | None = None
    current_student: int | None = None

class CourseResponse(BaseModel):
    id: int
    subject_id: int
    section: str
    professor: str | None = None
    room_id: int | None = None
    max_students: int | None = None
    current_student: int | None = None
    created_at: datetime

    class Config:
        from_attributes = True

class CourseScheduleResponse(BaseModel):
    id: int
    course_id: int
    day_of_week: str
    start_time: time
    end_time: time

    class Config:
        from_attributes = True

class CourseDetailResponse(BaseModel):
    id: int
    subject_id: int
    section: str
    professor: str | None = None
    schedule: list[CourseScheduleResponse] = []

    class Config:
        from_attributes = True

class CustomScheduleCreate(BaseModel):
    timetable_id: int
    name: str
    day_of_week: str
    start_time: time
    end_time: time
    color: str = "#3B82F6"
    memo: str | None = None

class CustomScheduleResponse(BaseModel):
    id: int
    timetable_id: int
    name: staticmethod
    day_of_weeK: str
    start_time: time
    end_time: time
    color: str
    memo: str | None = None

    class Config:
        from_attributes = True