from sqlalchemy.orm import Session, joinedload

from app.models import building, course_schedule, custom_schedule, room, subject  # noqa: F401
from app.models.course import Course
from app.models.custom_schedule import CustomSchedule
from app.models.timetable import Timetable
from app.models.timetable_course import TimetableCourse
from app.models.user import User
from app.schemas.timetable import CustomScheduleCreate, TimetableCourseCreate, TimetableCreate


def create_timetable(db: Session, user: User, data: TimetableCreate) -> Timetable:
    if data.is_main:
        db.query(Timetable).filter(Timetable.user_id == user.id).update({"is_main": False})

    timetable = Timetable(
        user_id=user.id,
        name=data.name,
        semester=data.semester,
        is_main=data.is_main,
    )
    db.add(timetable)
    db.commit()
    db.refresh(timetable)
    return timetable


def get_my_timetables(db: Session, user: User) -> list[Timetable]:
    return db.query(Timetable).filter(Timetable.user_id == user.id).order_by(Timetable.id.desc()).all()


def get_my_timetable(db: Session, user: User, timetable_id: int) -> Timetable | None:
    return (
        db.query(Timetable)
        .filter(Timetable.id == timetable_id, Timetable.user_id == user.id)
        .first()
    )


def get_my_timetable_detail(db: Session, user: User, timetable_id: int) -> dict | None:
    timetable = get_my_timetable(db, user, timetable_id)
    if not timetable:
        return None

    timetable_courses = (
        db.query(TimetableCourse)
        .filter(TimetableCourse.timetable_id == timetable_id)
        .all()
    )
    course_ids = [item.course_id for item in timetable_courses]
    color_by_course_id = {item.course_id: item.color for item in timetable_courses}

    courses = []
    if course_ids:
        course_rows = (
            db.query(Course)
            .options(joinedload(Course.subject), joinedload(Course.schedules))
            .filter(Course.id.in_(course_ids))
            .all()
        )
        for course in course_rows:
            courses.append(
                {
                    "id": course.id,
                    "subject_id": course.subject_id,
                    "subject_code": course.subject.subject_code if course.subject else None,
                    "name": course.subject.name if course.subject else None,
                    "credits": course.subject.credits if course.subject else None,
                    "section": course.section,
                    "professor": course.professor,
                    "color": color_by_course_id.get(course.id),
                    "schedules": course.schedules,
                }
            )

    custom_schedules = (
        db.query(CustomSchedule)
        .filter(CustomSchedule.timetable_id == timetable_id)
        .all()
    )

    return {
        "id": timetable.id,
        "user_id": timetable.user_id,
        "name": timetable.name,
        "semester": timetable.semester,
        "is_main": timetable.is_main,
        "share_token": timetable.share_token,
        "created_at": timetable.created_at,
        "courses": courses,
        "custom_schedules": custom_schedules,
        "total_credits": sum(course.get("credits") or 0 for course in courses),
    }


def add_course_to_timetable(
    db: Session,
    user: User,
    timetable_id: int,
    data: TimetableCourseCreate,
) -> TimetableCourse:
    timetable = get_my_timetable(db, user, timetable_id)
    if not timetable:
        raise ValueError("Timetable not found")

    course = db.query(Course).filter(Course.id == data.course_id).first()
    if not course:
        raise ValueError("Course not found")

    existing = (
        db.query(TimetableCourse)
        .filter(
            TimetableCourse.timetable_id == timetable_id,
            TimetableCourse.course_id == data.course_id,
        )
        .first()
    )
    if existing:
        raise ValueError("Course already added to timetable")

    timetable_course = TimetableCourse(
        timetable_id=timetable_id,
        course_id=data.course_id,
        color=data.color,
    )
    db.add(timetable_course)
    db.commit()
    db.refresh(timetable_course)
    return timetable_course


def remove_course_from_timetable(db: Session, user: User, timetable_id: int, course_id: int) -> None:
    timetable = get_my_timetable(db, user, timetable_id)
    if not timetable:
        raise ValueError("Timetable not found")

    timetable_course = (
        db.query(TimetableCourse)
        .filter(
            TimetableCourse.timetable_id == timetable_id,
            TimetableCourse.course_id == course_id,
        )
        .first()
    )
    if not timetable_course:
        raise ValueError("Timetable course not found")

    db.delete(timetable_course)
    db.commit()


def create_custom_schedule(
    db: Session,
    user: User,
    timetable_id: int,
    data: CustomScheduleCreate,
) -> CustomSchedule:
    timetable = get_my_timetable(db, user, timetable_id)
    if not timetable:
        raise ValueError("Timetable not found")

    schedule = CustomSchedule(
        timetable_id=timetable_id,
        name=data.name,
        day_of_week=data.day_of_week,
        start_time=data.start_time,
        end_time=data.end_time,
        color=data.color,
        memo=data.memo,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


def get_custom_schedules(db: Session, user: User, timetable_id: int) -> list[CustomSchedule]:
    timetable = get_my_timetable(db, user, timetable_id)
    if not timetable:
        raise ValueError("Timetable not found")

    return db.query(CustomSchedule).filter(CustomSchedule.timetable_id == timetable_id).all()


def delete_custom_schedule(db: Session, user: User, timetable_id: int, schedule_id: int) -> None:
    timetable = get_my_timetable(db, user, timetable_id)
    if not timetable:
        raise ValueError("Timetable not found")

    schedule = (
        db.query(CustomSchedule)
        .filter(CustomSchedule.id == schedule_id, CustomSchedule.timetable_id == timetable_id)
        .first()
    )
    if not schedule:
        raise ValueError("Custom schedule not found")

    db.delete(schedule)
    db.commit()
