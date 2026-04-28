from sqlalchemy.orm import Session, joinedload

from app.crawlers.course_crawler import parse_course_list_html, save_courses
from app.models.course import Course
from app.models.subject import Subject
from app.models.course_schedule import CourseSchedule


def import_courses_from_html(db: Session, html: str, department: str | None = None, save: bool = True) -> dict:
    parsed_courses = parse_course_list_html(html, department=department)
    saved_count = save_courses(db, parsed_courses) if save else 0
    return {
        "parsed_count": len(parsed_courses),
        "saved_count": saved_count,
        "items": parsed_courses,
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
