from __future__ import annotations

from sqlalchemy.orm import Session, joinedload

from app.models.course import Course
from app.models.custom_schedule import CustomSchedule
from app.models.room import Room
from app.models.timetable import Timetable
from app.models.timetable_course import TimetableCourse
from app.models.user import User


# 시간표와 관계없는 질문에는 개인 데이터를 읽지 않는다. 단어는 실제 사용 중
# 늘릴 수 있지만, 너무 넓은 단어(예: "오늘")만으로는 조회하지 않는다.
TIMETABLE_CONTEXT_KEYWORDS = (
    "시간표",
    "수업",
    "강의",
    "공강",
    "강의실",
    "교시",
    "과목",
    "내 일정",
    "내일정",
    "오늘 일정",
    "내일 일정",
    "내 스케줄",
)

DAY_LABELS = {
    "MON": "월요일",
    "TUE": "화요일",
    "WED": "수요일",
    "THU": "목요일",
    "FRI": "금요일",
    "SAT": "토요일",
    "SUN": "일요일",
}

SHARED_RAG_KEYWORDS = (
    "공지", "학사일정", "학칙", "규정", "장학", "등록금", "셔틀", "버스",
    "학식", "메뉴", "도서관", "졸업", "수강신청", "휴강", "보강",
    "시험", "중간고사", "기말고사", "행사",
)


def needs_timetable_context(question: str) -> bool:
    normalized_question = question.replace(" ", "").lower()
    return any(
        keyword.replace(" ", "").lower() in normalized_question
        for keyword in TIMETABLE_CONTEXT_KEYWORDS
    )


def is_timetable_only_query(question: str) -> bool:
    """Whether the user's timetable alone can answer this timetable question."""
    normalized_question = question.replace(" ", "").lower()
    has_shared_intent = any(
        keyword.replace(" ", "").lower() in normalized_question
        for keyword in SHARED_RAG_KEYWORDS
    )
    return needs_timetable_context(question) and not has_shared_intent


def _format_time(value) -> str:
    return value.strftime("%H:%M") if value else "시간 미정"


def _format_day(day_of_week: str | None) -> str:
    if not day_of_week:
        return "요일 미정"
    return DAY_LABELS.get(day_of_week.upper(), day_of_week)


def build_main_timetable_context(db: Session, user: User) -> str:
    """현재 사용자의 대표 시간표를 AI가 읽을 수 있는 짧은 문장으로 만든다.

    개인 시간표는 벡터 DB에 색인하지 않는다. 이 함수는 이미 인증된 사용자의
    데이터만 한 번의 eager-loading 조회로 읽으므로, 수정·삭제가 즉시 반영된다.
    """
    timetable = (
        db.query(Timetable)
        .options(
            joinedload(Timetable.courses)
            .joinedload(TimetableCourse.course)
            .joinedload(Course.subject),
            joinedload(Timetable.courses)
            .joinedload(TimetableCourse.course)
            .joinedload(Course.schedules),
            joinedload(Timetable.courses)
            .joinedload(TimetableCourse.course)
            .joinedload(Course.room)
            .joinedload(Room.building),
            joinedload(Timetable.courses).joinedload(TimetableCourse.building),
            joinedload(Timetable.custom_schedules).joinedload(CustomSchedule.building),
        )
        .filter(Timetable.user_id == user.id, Timetable.is_main.is_(True))
        .first()
    )

    if timetable is None:
        return "[사용자 개인 시간표]\n대표 시간표가 아직 등록되어 있지 않습니다."

    entries: list[tuple[str, str]] = []
    for timetable_course in timetable.courses:
        course = timetable_course.course
        if course is None:
            continue

        subject_name = course.subject.name if course.subject else "이름 없는 과목"
        professor = course.professor or "담당 교수 미정"
        building = timetable_course.building or (
            course.room.building if course.room else None
        )
        place_parts = [building.name] if building else []
        if course.room and course.room.room_number:
            place_parts.append(course.room.room_number)
        place = " ".join(place_parts) or "강의실 미정"

        for schedule in course.schedules:
            sort_key = f"{schedule.day_of_week}-{_format_time(schedule.start_time)}"
            entries.append(
                (
                    sort_key,
                    f"- {_format_day(schedule.day_of_week)} "
                    f"{_format_time(schedule.start_time)}~{_format_time(schedule.end_time)}: "
                    f"{subject_name} / {professor} / {place}",
                )
            )

    for schedule in timetable.custom_schedules:
        place = schedule.building.name if schedule.building else "장소 미정"
        memo = f" / 메모: {schedule.memo}" if schedule.memo else ""
        sort_key = f"{schedule.day_of_week}-{_format_time(schedule.start_time)}"
        entries.append(
            (
                sort_key,
                f"- {_format_day(schedule.day_of_week)} "
                f"{_format_time(schedule.start_time)}~{_format_time(schedule.end_time)}: "
                f"{schedule.name} / 개인 일정 / {place}{memo}",
            )
        )

    lines = [f"[사용자 개인 시간표: {timetable.name} / {timetable.semester}]"]
    if entries:
        lines.extend(entry for _, entry in sorted(entries))
    else:
        lines.append("등록된 수업 또는 개인 일정이 없습니다.")
    lines.append("이 정보는 현재 질문을 보낸 사용자에게만 해당합니다.")
    return "\n".join(lines)
