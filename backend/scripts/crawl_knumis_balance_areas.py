"""종합정보 시스템 균형교양 영역 수동 크롤러."""

from __future__ import annotations

import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.crawlers.course_crawler import crawl_knumis_course_list  # noqa: E402
from app.crawlers.course_crawler import save_courses  # noqa: E402
from app.database import SessionLocal  # noqa: E402


# 현재 브라우저 요청에서 확인된 교양 영역 코드입니다.
BALANCE_AREAS = [
    ("균형교양 1영역", "G31"),
    ("균형교양 2영역", "G32"),
    ("균형교양 3영역", "G333"),
    ("균형교양 4영역", "G344"),
    ("일반교양", "G19"),
    ("자율선택", "G9"),
]


def crawl_balance_areas(
    session_cookie: str,
    *,
    year: str,
    semester: str,
    student_number: str,
    student_grade: str,
    student_department_code: str,
    fact_code: str,
    delay_seconds: float = 1.0,
) -> None:
    db = SessionLocal()
    total_courses = 0
    total_saved = 0
    try:
        for label, area_code in BALANCE_AREAS:
            print(f"\n{label}({area_code}) 조회 중...")
            try:
                courses = crawl_knumis_course_list(
                    session_cookie=session_cookie,
                    year=year,
                    semester=semester,
                    department_code="",
                    department=label,
                    student_number=student_number,
                    student_grade=student_grade,
                    student_department_code=student_department_code,
                    fact_code=fact_code,
                    fact_srch=student_department_code,
                    grad_srch="",
                    grad_area1=area_code,
                    grad_area2="H4",
                )
                for course in courses:
                    course["course_type"] = label
                saved = save_courses(db, courses)
                total_courses += len(courses)
                total_saved += saved
                print(f"  검색 {len(courses)}개 / 새 분반 저장 {saved}개")
            except Exception as exc:
                print(f"  실패: {exc}")

            if delay_seconds > 0:
                time.sleep(delay_seconds)
    finally:
        db.close()

    print("\n균형교양 크롤링 완료")
    print(f"검색 과목 수: {total_courses}개")
    print(f"새로 저장된 분반: {total_saved}개")


if __name__ == "__main__":
    if len(sys.argv) < 8:
        print(
            "사용법: python scripts/crawl_knumis_balance_areas.py "
            '"전체 Cookie" 연도 학기 학번 학년 학생학과코드 단과대코드 [지연초]'
        )
        raise SystemExit(1)

    crawl_balance_areas(
        sys.argv[1],
        year=sys.argv[2],
        semester=sys.argv[3],
        student_number=sys.argv[4],
        student_grade=sys.argv[5],
        student_department_code=sys.argv[6],
        fact_code=sys.argv[7],
        delay_seconds=float(sys.argv[8]) if len(sys.argv) > 8 else 1.0,
    )
