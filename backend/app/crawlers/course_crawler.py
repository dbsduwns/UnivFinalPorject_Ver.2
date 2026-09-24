from __future__ import annotations

import re
import time as time_module
from datetime import time

import requests
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

KNU_COURSE_LIST_URL = "https://app.kangnam.ac.kr/knumis/sbr/sbr3070L.jsp"
KNU_COURSE_SEARCH_PAGE_URL = "https://app.kangnam.ac.kr/knumis/sbr/sbr3070T.jsp"


def _normalize_session_cookie(session_cookie: str) -> str:
    """종합정보 시스템 요청에 사용할 JSESSIONID 쿠키를 정규화합니다."""
    cookie = session_cookie.strip()
    if not cookie:
        raise ValueError("JSESSIONID가 비어 있습니다.")
    if "=" not in cookie:
        cookie = f"JSESSIONID={cookie}"
    return cookie


def _decode_knumis_response(response: requests.Response) -> str:
    """KNUMIS의 EUC-KR/CP949 응답을 안전하게 문자열로 변환합니다."""
    for encoding in ("euc-kr", "cp949", "utf-8"):
        try:
            return response.content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return response.text


def _selected_value(soup: BeautifulSoup, field_name: str) -> str:
    """hidden/input/select에서 종합정보 시스템의 기본 검색값을 읽습니다."""
    element = soup.select_one(f"input[name='{field_name}']")
    if element:
        return str(element.get("value") or "").strip()

    select = soup.select_one(f"select[name='{field_name}']")
    if select:
        selected = select.select_one("option[selected]") or select.select_one("option")
        if selected:
            return str(selected.get("value") or "").strip()

    return ""


def _load_knumis_search_defaults(
    session_cookie: str,
    *,
    timeout: int = 20,
) -> dict[str, str]:
    """JSESSIONID로 종합정보 시스템 검색 화면의 기본값을 가져옵니다."""
    cookie = _normalize_session_cookie(session_cookie)
    response = requests.get(
        KNU_COURSE_SEARCH_PAGE_URL,
        headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ko,en-US;q=0.9,en;q=0.8",
            "Cookie": cookie,
            "Referer": "https://app.kangnam.ac.kr/knumis/main/main.jsp",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/153.0.0.0 Safari/537.36",
        },
        timeout=timeout,
    )
    response.raise_for_status()
    html = _decode_knumis_response(response)

    # 정상적인 종합정보 화면에도 '로그인/로그아웃' 문자열이 포함될 수 있으므로
    # 세션 만료 안내 문구만 실패 신호로 사용합니다.
    if any(token in html for token in ("세션이 만료", "시간이 만료", "로그인 후 이용")):
        raise ValueError("종합정보 시스템 세션이 만료되었거나 JSESSIONID가 유효하지 않습니다.")

    soup = BeautifulSoup(html, "html.parser")
    return {
        "student_number": _selected_value(soup, "stnt_numb"),
        "student_grade": _selected_value(soup, "stnt_grad"),
        "student_department_code": _selected_value(soup, "stnt_dept"),
        "fact_code": _selected_value(soup, "fact_code"),
        "fact_srch": _selected_value(soup, "fact_srch"),
        "student_dorn": _selected_value(soup, "stnt_dorn") or "1",
        "dept_code2": _selected_value(soup, "dept_code2") or "5100",
        "grad_area1": _selected_value(soup, "grad_area1") or "H4",
        "grad_area2": _selected_value(soup, "grad_area2") or "H4",
    }


def crawl_knumis_course_list(
    *,
    session_cookie: str,
    year: str,
    semester: str,
    department_code: str,
    department: str | None = None,
    student_number: str | None = None,
    student_grade: str | None = None,
    student_department_code: str | None = None,
    fact_code: str | None = None,
    fact_srch: str | None = None,
    srch_gubn: str = "41",
    grad_srch: str | None = None,
    grad_area1: str = "H4",
    grad_area2: str = "H4",
    timeout: int = 20,
) -> list[dict]:
    """JSESSIONID만으로 종합정보 시스템의 한 학과 과목을 조회합니다."""
    # 브라우저의 전체 Cookie와 검색 폼 값을 전달하면 초기 화면 자동 추출을
    # 건너뛸 수 있습니다. 종합정보 시스템이 초기 화면에서 빈 프레임을 반환하는
    # 경우(현재 확인된 상황)를 위한 명시적 요청 경로입니다.
    needs_defaults = any(
        value is None
        for value in (
            student_number,
            student_grade,
            student_department_code,
            fact_code,
            fact_srch,
        )
    )
    defaults = _load_knumis_search_defaults(session_cookie, timeout=timeout) if needs_defaults else {}
    html = crawl_course_list_html(
        session_cookie=_normalize_session_cookie(session_cookie),
        year=year,
        semester=semester,
        department_code=department_code,
        student_number=student_number if student_number is not None else defaults["student_number"],
        student_grade=student_grade if student_grade is not None else defaults["student_grade"],
        student_department_code=(
            student_department_code
            if student_department_code is not None
            else defaults["student_department_code"]
        ),
        fact_code=fact_code if fact_code is not None else defaults["fact_code"],
        fact_srch=(
            fact_srch
            if fact_srch is not None
            else defaults["fact_srch"] or department_code
        ),
        srch_gubn=srch_gubn,
        student_dorn=defaults.get("student_dorn", "1"),
        grad_srch=(
            grad_srch
            if grad_srch is not None
            else (student_grade if student_grade is not None else defaults.get("student_grade", ""))
        ),
        dept_code2=defaults.get("dept_code2", "5100"),
        grad_area1=grad_area1,
        grad_area2=grad_area2,
        timeout=timeout,
    )
    return parse_course_list_html(
        html,
        department=department,
        semester_override=f"{year}-{semester}",
    )


def parse_course_list_html(
    html: str,
    department: str | None = None,
    semester_override: str | None = None,
) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("table.grid_list tr")
    courses = []

    year_el = soup.select_one("input[name='schl_year']")
    semester_el = soup.select_one("input[name='schl_smst']")
    year = year_el.get("value") if year_el else None
    semester_number = semester_el.get("value") if semester_el else None
    semester = semester_override or (f"{year}-{semester_number}" if year and semester_number else "")

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


def crawl_course_list_html(
    *,
    session_cookie: str,
    year: str,
    semester: str,
    department_code: str,
    student_number: str,
    student_grade: str,
    student_department_code: str,
    fact_code: str,
    fact_srch: str,
    srch_gubn: str = "41",
    student_dorn: str = "1",
    grad_srch: str | None = None,
    dept_code2: str = "5100",
    grad_area1: str = "H4",
    grad_area2: str = "H4",
    timeout: int = 20,
    ) -> str:
    form_data = {
        "schl_year": year,
        "schl_smst": semester,
        "stnt_numb": student_number,
        "dept_srch": department_code,
        "srch_gubn": srch_gubn,
        "stnt_grad": student_grade,
        "stnt_dept": student_department_code,
        "fact_code": fact_code,
        "stnt_dorn": student_dorn,
        "subj_knam": "",
        "subj_knam2": "",
        "fact_srch": fact_srch,
        # None이면 학생 학년을 기본값으로 사용하고,
        # 빈 문자열이면 전체 학년 검색 조건을 그대로 전송합니다.
        "grad_srch": student_grade if grad_srch is None else grad_srch,
        "dept_code1": department_code,
        "grad_area1": grad_area1,
        "dept_code2": dept_code2,
        "grad_area2": grad_area2,
    }

    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "ko,en-US;q=0.9,en;q=0.8",
        "Cache-Control": "max-age=0",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded",
        "Cookie": session_cookie,
        "DNT": "1",
        "Origin": "https://app.kangnam.ac.kr",
        "Referer": "https://app.kangnam.ac.kr/knumis/sbr/sbr3070T.jsp",
        "Sec-Fetch-Dest": "frame",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36",
        "sec-ch-ua": '"Google Chrome";v="153", "Not_A Brand";v="8", "Chromium";v="153"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    }

    response = requests.post(
        KNU_COURSE_LIST_URL,
        data=form_data,
        headers=headers,
        timeout=timeout,
    )
    response.raise_for_status()

    for encoding in ("euc-kr", "cp949", "utf-8"):
        try:
            return response.content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return response.text


def crawl_department_courses(
    *,
    session_cookie: str,
    year: str,
    semester: str,
    departments: list[dict],
    student_number: str,
    student_grade: str,
    student_department_code: str,
    fact_code: str,
    fact_srch: str,
    student_dorn: str = "1",
    grad_srch: str | None = None,
    dept_code2: str = "5100",
    grad_area1: str = "H4",
    grad_area2: str = "H4",
    delay_seconds: float = 1.0,
) -> list[dict]:
    results = []
    for index, department in enumerate(departments):
        code = department["code"]
        name = department.get("name") or code
        try:
            html = crawl_course_list_html(
                session_cookie=session_cookie,
                year=year,
                semester=semester,
                department_code=code,
                student_number=student_number,
                student_grade=student_grade,
                student_department_code=student_department_code,
                fact_code=fact_code,
                fact_srch=fact_srch,
                student_dorn=student_dorn,
                grad_srch=grad_srch,
                dept_code2=dept_code2,
                grad_area1=grad_area1,
                grad_area2=grad_area2,
            )
            parsed_courses = parse_course_list_html(html, department=name)
            for course in parsed_courses:
                course["course_type"] = department.get("course_type")
            results.append(
                {
                    "department_code": code,
                    "department_name": name,
                    "parsed_count": len(parsed_courses),
                    "items": parsed_courses,
                    "error": None,
                }
            )
        except Exception as exc:
            results.append(
                {
                    "department_code": code,
                    "department_name": name,
                    "parsed_count": 0,
                    "items": [],
                    "error": str(exc),
                }
            )

        if delay_seconds > 0 and index < len(departments) - 1:
            time_module.sleep(delay_seconds)

    return results


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
            .filter(
                Subject.subject_code == item["subject_code"],
                Subject.semester == item["semester"],
            )
            .first()
        )
        if not subject:
            subject = Subject(
                name=item["name"],
                subject_code=item["subject_code"],
                department=item.get("department"),
                credits=item["credits"],
                course_type=item.get("course_type"),
                semester=item["semester"],
            )
            db.add(subject)
            db.flush()
        else:
            subject.name = item["name"]
            subject.department = item.get("department")
            subject.credits = item["credits"]
            if "course_type" in item:
                subject.course_type = item.get("course_type")
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
