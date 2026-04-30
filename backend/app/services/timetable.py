from sqlalchemy.orm import Session, joinedload

from app.models import building, course_schedule, custom_schedule, room, subject  # noqa: F401
from app.models.course import Course
from app.models.custom_schedule import CustomSchedule
from app.models.timetable import Timetable
from app.models.timetable_course import TimetableCourse
from app.models.user import User
from app.schemas.timetable import CustomScheduleCreate, CustomScheduleUpdate, TimetableCourseCreate, TimetableCreate, TimetableUpdate


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

def update_timetable(
        db: Session,
        user: User,
        timetable_id: int,
        data: TimetableUpdate
    ) -> Timetable:
    timetable = get_my_timetable(db, user, timetable_id)
    if not timetable:
        raise ValueError("Timetable not Found")
    
    update_data = data.model_dump(exclude_unset=True)

    if update_data.get("is_main") is True:
        db.query(Timetable).filter(
            Timetable.user_id == user.id,
            Timetable.id == timetable.id,
        ).update({"is_main":False})

    for field, value in update_data.items():
        setattr(timetable, field, value)

    db.commit()
    db.refresh(timetable)
    return timetable

def delete_timetable(db: Session, user: User, timetable_id: int) -> None:
    timetable = get_my_timetable(db, user, timetable_id)
    if not timetable:
        raise ValueError("Timetable not found")
    
    db.query(TimetableCourse).filter(
        TimetableCourse.timetable_id == timetable_id
    ).delete()

    db.query(CustomSchedule).filter(
        CustomSchedule.timetable_id == timetable_id
    ).delete()

    db.delete(timetable)
    db.commit()
    

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

def _has_time_overlap(a_start, a_end, b_start, b_end) -> bool:
    return a_start < b_end and a_end > b_start

def _validate_schedules_no_conflict(
        db: Session,
        timetable_id: int,
        new_schedules,
        exclude_custom_schedule_id: int | None = None,) -> None:
    existing_course_ids = [
        item.course_id
        for item in db.query(TimetableCourse)
        .filter(TimetableCourse.timetable_id == timetable_id)
        .all()
    ]

    existing_courses = []
    if existing_course_ids:
        existing_courses = (
            db.query(Course)
            .options(joinedload(Course.schedules), joinedload(Course.subject))
            .filter(Course.id.in_(existing_course_ids))
            .all()
        )

    for new_schedule in new_schedules:
        for existing_course in existing_courses:
            for existing_schedule in existing_course.schedules:
                if (
                    new_schedule.day_of_week == existing_schedule.day_of_week
                    and _has_time_overlap(
                        new_schedule.start_time,
                        new_schedule.end_time,
                        existing_schedule.start_time,
                        existing_schedule.end_time,
                    )
                ):
                    name = existing_course.subject.name if existing_course.subject else "existing course"
                    raise ValueError(f"Time conflict with course {name}")

    custom_query = db.query(CustomSchedule).filter(
        CustomSchedule.timetable_id == timetable_id
    )

    if exclude_custom_schedule_id is not None:
        custom_query = custom_query.filter(
            CustomSchedule.id != exclude_custom_schedule_id
        )

    custom_schedules = custom_query.all()

    for new_schedule in new_schedules:
        for custom_schedule in custom_schedules:
            if (
                new_schedule.day_of_week == custom_schedule.day_of_week
                and _has_time_overlap(
                    new_schedule.start_time,
                    new_schedule.end_time,
                    custom_schedule.start_time,
                    custom_schedule.end_time,
                )
            ):
                raise ValueError(f"Time conflict with custom schedule {custom_schedule.name}")

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

    _validate_schedules_no_conflict(db, timetable_id, course.schedules)

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

    if schedule.start_time >= schedule.end_time:
        raise ValueError("Custom schedule start_time must be before end_time")
    
    _validate_schedules_no_conflict(db, timetable_id, [schedule])

    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


def get_custom_schedules(db: Session, user: User, timetable_id: int) -> list[CustomSchedule]:
    timetable = get_my_timetable(db, user, timetable_id)
    if not timetable:
        raise ValueError("Timetable not found")

    return db.query(CustomSchedule).filter(CustomSchedule.timetable_id == timetable_id).all()

def update_custom_schedule(
        db: Session,
        user: User,
        timetable_id: int,
        schedule_id: int,
        data: CustomScheduleUpdate,
        ) -> CustomSchedule:
    
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
    
    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(schedule, field, value)

    if schedule.start_time >= schedule.end_time:
        raise ValueError("Custom schedule start_time must be before end_time")
    
    _validate_schedules_no_conflict(db, timetable_id, [schedule], exclude_custom_schedule_id=schedule_id)

    db.commit()
    db.refresh(schedule)
    return schedule
   
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
