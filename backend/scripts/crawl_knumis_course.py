"""종합정보 시스템 과목 수동 크롤러.

수강신청 전용 KN_SUGANG_SESSION은 사용하지 않고,
종합정보 시스템의 JSESSIONID만 사용합니다.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# backend 디렉터리를 import 경로에 추가합니다.
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.crawlers.course_crawler import crawl_knumis_course_list
from app.crawlers.course_crawler import save_courses
from app.database import SessionLocal


DEFAULT_YEAR = "2026"
DEFAULT_SEMESTER = "2"
DEFAULT_DEPARTMENT_CODE = "5446"  # 소프트웨어전공(ICT융합공학부)
DEPARTMENT_CODES_PATH = BACKEND_DIR / "data" / "department_codes_all.json"


def find_department_name(department_code: str) -> str:
    if not DEPARTMENT_CODES_PATH.exists():
        return department_code

    try:
        departments = json.loads(DEPARTMENT_CODES_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return department_code

    for department in departments:
        if str(department.get("code")) == department_code:
            return str(department.get("name") or department_code)
    return department_code


def crawl_and_save(
    session_cookie: str,
    *,
    year: str = DEFAULT_YEAR,
    semester: str = DEFAULT_SEMESTER,
    department_code: str = DEFAULT_DEPARTMENT_CODE,
    student_number: str | None = None,
    student_grade: str | None = None,
    student_department_code: str | None = None,
    fact_code: str | None = None,
    fact_srch: str | None = None,
) -> None:
    department_name = find_department_name(department_code)
    print(
        f"종합정보 시스템 과목 크롤링 시작: "
        f"{year}-{semester}, {department_name}({department_code})"
    )

    courses = crawl_knumis_course_list(
        session_cookie=session_cookie,
        year=year,
        semester=semester,
        department_code=department_code,
        department=department_name,
        student_number=student_number,
        student_grade=student_grade,
        student_department_code=student_department_code,
        fact_code=fact_code,
        fact_srch=fact_srch,
    )
    print(f"검색된 과목 수: {len(courses)}개")

    db = SessionLocal()
    try:
        saved_count = save_courses(db, courses)
        print(f"DB 저장 완료: 새 분반 {saved_count}개")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "사용법: python scripts/crawl_knumis_course.py "
            '"전체 Cookie" [연도] [학기] [학과코드] '
            '[학번] [학년] [학생학과코드] [단과대코드] [검색학과코드]'
        )
        print(
            "예시: python scripts/crawl_knumis_course.py "
            '"JSESSIONID=...; 기타쿠키=..." 2026 2 5446 '
            '202104255 4 5446 5444 5446'
        )
        raise SystemExit(1)

    cookie = sys.argv[1]
    target_year = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_YEAR
    target_semester = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_SEMESTER
    target_department = (
        sys.argv[4] if len(sys.argv) > 4 else DEFAULT_DEPARTMENT_CODE
    )
    profile_values = [sys.argv[index] if len(sys.argv) > index else None for index in range(5, 10)]

    crawl_and_save(
        cookie,
        year=target_year,
        semester=target_semester,
        department_code=target_department,
        student_number=profile_values[0],
        student_grade=profile_values[1],
        student_department_code=profile_values[2],
        fact_code=profile_values[3],
        fact_srch=profile_values[4],
    )
