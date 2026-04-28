from __future__ import annotations

import re
from datetime import time

from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.course_schedule import CourseSchedule
from app.models.subject import Subject


PERIOD_TIME_MAP = {
    "1": (time(9, 0), time(9, 50)),
    "2": (time(10, 0), time(10, 50)),
    "3": (time(11, 0), time(11, 50)),
    "4": (time(12, 0), time(12, 50)),
    "5": (time(13, 0), time(13, 50)),
    "6": (time(14, 0), time(14, 50)),
    "7": (time(15, 0), time(15, 50)),
    "8": (time(16, 0), time(16, 50)),
    "9": (time(17, 0), time(17, 50)),
}

DAY_MAP = {
    "월": "MON",
    "화": "TUE",
    "수": "WED",
    "목": "THU",
    "금": "FRI",
    "토": "SAT",
    "일": "SUN",
    "MON": "MON",
    "TUE": "TUE",
    "WED": "WED",
    "THU": "THU",
    "FRI": "FRI",
    "SAT": "SAT",
    "SUN": "SUN",
}


def parse_course_list_html(html: str, department: str | None = None) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("table.grid_list tr")
    courses = []

    year_el = soup.select_one("input[name='schl_year']")
    semester_el = soup.select_one("input[name='schl_smst']")
    year = year_el.get("value") if year_el else None
    semester_number = semester_el.get("value") if semester_el else None
    semester = f"{year}-{semester_number}" if year and semester_number else ""

    for row in rows:
        cells = row.select("td")
        if len(cells) < 7:
            continue

        subject_code = cells[0].get_text(strip=True)
        section = cells[1].get_text(strip=True)
        name = cells[2].get_text(strip=True)
        professor = cells[3].get_text(strip=True) or None
        credits = _to_int(cells[4].get_text(strip=True), default=0)
        hours = _to_int(cells[5].get_text(strip=True), default=0)
        schedule_text = cells[6].get_text(strip=True)

        if not subject_code or not section or not name:
            continue

        courses.append(
            {
                "subject_code": subject_code,
                "section": section,
                "name": name,
                "professor": professor,
                "credits": credits,
                "hours": hours,
                "schedule_text": schedule_text,
                "semester": semester,
                "department": department,
                "schedules": parse_schedule_text(schedule_text),
            }
        )

    return courses


def parse_schedule_text(schedule_text: str) -> list[dict]:
    if not schedule_text:
        return []

    schedules = []
    for chunk in schedule_text.split(","):
        match = re.search(r"(월|화|수|목|금|토|일|MON|TUE|WED|THU|FRI|SAT|SUN)([0-9ab]+)", chunk)
        if not match:
            continue

        day = DAY_MAP[match.group(1)]
        periods = re.findall(r"\d+", match.group(2))
        if not periods:
            continue

        first = periods[0]
        last = periods[-1]
        if first not in PERIOD_TIME_MAP or last not in PERIOD_TIME_MAP:
            continue

        start_time = PERIOD_TIME_MAP[first][0]
        end_time = PERIOD_TIME_MAP[last][1]
        schedules.append(
            {
                "day_of_week": day,
                "start_time": start_time,
                "end_time": end_time,
            }
        )

    return schedules


def save_courses(db: Session, parsed_courses: list[dict]) -> int:
    saved_count = 0
    for item in parsed_courses:
        subject = (
            db.query(Subject)
            .filter(Subject.subject_code == item["subject_code"])
            .first()
        )
        if not subject:
            subject = Subject(
                name=item["name"],
                subject_code=item["subject_code"],
                department=item.get("department"),
                credits=item["credits"],
                course_type=None,
                semester=item["semester"],
            )
            db.add(subject)
            db.flush()
        else:
            subject.name = item["name"]
            subject.department = item.get("department")
            subject.credits = item["credits"]
            subject.semester = item["semester"]

        course = (
            db.query(Course)
            .filter(Course.subject_id == subject.id, Course.section == item["section"])
            .first()
        )
        if not course:
            course = Course(
                subject_id=subject.id,
                section=item["section"],
                professor=item["professor"],
            )
            db.add(course)
            db.flush()
            saved_count += 1
        else:
            course.professor = item["professor"]

        db.query(CourseSchedule).filter(CourseSchedule.course_id == course.id).delete()
        for schedule in item["schedules"]:
            db.add(
                CourseSchedule(
                    course_id=course.id,
                    day_of_week=schedule["day_of_week"],
                    start_time=schedule["start_time"],
                    end_time=schedule["end_time"],
                )
            )

    db.commit()
    return saved_count


def _to_int(value: str, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
