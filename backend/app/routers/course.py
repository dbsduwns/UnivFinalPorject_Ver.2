from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.course import (
    CourseImportRequest,
    CourseImportResponse,
    CourseResponse,
    DepartmentCourseCrawlRequest,
    DepartmentCourseCrawlResponse,
)
from app.services import course as course_service
from app.core.dependencies import get_current_admin_user
from app.models.user import User

router = APIRouter(prefix="/api/courses", tags=["courses"])


@router.post("/import-html", response_model=CourseImportResponse)
def import_courses_from_html(
    data: CourseImportRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user), # 관리자 검증
):
    return course_service.import_courses_from_html(
        db,
        html=data.html,
        department=data.department,
        save=data.save,
    )


@router.post("/import-html-file", response_model=CourseImportResponse)
async def import_courses_from_html_file(
    file: UploadFile = File(...),
    department: str | None = Form(default=None),
    save: bool = Form(default=True),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user), # 관리자 검증
):
    content = await file.read()
    try:
        html = content.decode("utf-8")
    except UnicodeDecodeError:
        html = content.decode("cp949")

    return course_service.import_courses_from_html(
        db,
        html=html,
        department=department,
        save=save,
    )


@router.post("/crawl-departments", response_model=DepartmentCourseCrawlResponse)
def crawl_department_courses(
    data: DepartmentCourseCrawlRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user), # 관리자 검증
):
    try:
        return course_service.crawl_and_import_department_courses(db, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=list[CourseResponse])
def get_courses(
    keyword: str | None = None,
    department: str | None = None,
    professor: str | None = None,
    semester: str | None = None,
    day_of_week: str | None = None,
    credits: int | None = None,
    subject_code: str | None = None, 
    db: Session = Depends(get_db)):

    return course_service.get_courses(
        db,
        keyword=keyword, 
        department=department,
        professor=professor,
        semester=semester,
        day_of_week=day_of_week,
        credits=credits,
        subject_code=subject_code)


@router.get("/{course_id}", response_model=CourseResponse)
def get_course(course_id: int, db: Session = Depends(get_db)):
    course = course_service.get_course(db, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course
