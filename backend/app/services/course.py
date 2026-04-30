from sqlalchemy.orm import Session, joinedload

from app.crawlers.course_crawler import crawl_department_courses, parse_course_list_html, save_courses
from app.models.course import Course
from app.models.subject import Subject
from app.models.course_schedule import CourseSchedule
from app.schemas.course import DepartmentCourseCrawlRequest


def import_courses_from_html(db: Session, html: str, department: str | None = None, save: bool = True) -> dict:
    parsed_courses = parse_course_list_html(html, department=department)
    saved_count = save_courses(db, parsed_courses) if save else 0
    return {
        "parsed_count": len(parsed_courses),
        "saved_count": saved_count,
        "items": parsed_courses,
    }


def crawl_and_import_department_courses(db: Session, data: DepartmentCourseCrawlRequest) -> dict:
    if not data.departments:
        raise ValueError("departments must not be empty")

    departments = [item.model_dump() for item in data.departments]
    crawl_results = crawl_department_courses(
        session_cookie=data.session_cookie,
        year=data.year,
        semester=data.semester,
        departments=departments,
        student_number=data.student_number,
        student_grade=data.student_grade,
        student_department_code=data.student_department_code,
        fact_code=data.fact_code,
        fact_srch=data.fact_srch,
        student_dorn=data.student_dorn,
        grad_srch=data.grad_srch,
        dept_code2=data.dept_code2,
        grad_area1=data.grad_area1,
        grad_area2=data.grad_area2,
        delay_seconds=data.delay_seconds,
    )

    response_results = []
    total_parsed_count = 0
    total_saved_count = 0
    for result in crawl_results:
        saved_count = 0
        parsed_courses = result["items"]
        total_parsed_count += result["parsed_count"]
        if data.save and not result["error"]:
            saved_count = save_courses(db, parsed_courses)
            total_saved_count += saved_count

        response_results.append(
            {
                "department_code": result["department_code"],
                "department_name": result["department_name"],
                "parsed_count": result["parsed_count"],
                "saved_count": saved_count,
                "error": result["error"],
            }
        )

    return {
        "department_count": len(data.departments),
        "parsed_count": total_parsed_count,
        "saved_count": total_saved_count,
        "results": response_results,
    }


def get_courses(
        db: Session,
        keyword: str | None = None, 
        department: str | None = None,
        professor: str | None = None,
        semester: str | None = None,
        day_of_week: str | None = None,
        credits: int | None = None,
        subject_code: str | None = None,
        )-> list[Course]:
    
    query = db.query(Course).options(joinedload(Course.subject), joinedload(Course.schedules))

    needs_subject_join = any([
        keyword,
        department,
        semester,
        credits is not None,
        subject_code,
    ])

    if needs_subject_join:
        query = query.join(Subject)

    if keyword:
        query = query.filter(Subject.name.contains(keyword))
    if department:
        query = query.filter(Subject.department.contains(department))
    if professor:
        query = query.filter(Course.professor.contains(professor))
    if semester:
        query = query.filter(Subject.semester == semester)
    if day_of_week:
        query = query.join(CourseSchedule).filter(CourseSchedule.day_of_week == day_of_week)
    if credits:
        query = query.filter(Subject.credits == credits)
    if subject_code:
        query = query.filter(Subject.subject_code.contains(subject_code))

    return query.order_by(Course.id.desc()).all()



def get_course(db: Session, course_id: int) -> Course | None:
    return (
        db.query(Course)
        .options(joinedload(Course.subject), joinedload(Course.schedules))
        .filter(Course.id == course_id)
        .first()
    )
