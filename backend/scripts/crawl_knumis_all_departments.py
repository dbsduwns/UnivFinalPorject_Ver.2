"""종합정보 시스템의 전체 전공 과목 수동 크롤러."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.crawlers.course_crawler import crawl_knumis_course_list  # noqa: E402
from app.crawlers.course_crawler import save_courses  # noqa: E402
from app.database import SessionLocal  # noqa: E402


DEPARTMENT_CODES_PATH = BACKEND_DIR / "data" / "department_codes_all.json"
SEARCH_CODES_PATH = BACKEND_DIR / "data" / "knumis_search_codes.json"
DEFAULT_YEAR = "2026"
DEFAULT_SEMESTER = "2"
DEFAULT_DELAY_SECONDS = 1.0
TARGET_GRADES = ("1", "2", "3", "4")
DEFAULT_GRADE_AREAS = {
    "1": "H1",
    "2": "H2",
    "3": "H3",
    "4": "H4",
}

FALLBACK_BALANCE_AREAS = [
    {"code": "G31", "name": "균형교양 1영역"},
    {"code": "G32", "name": "균형교양 2영역"},
    {"code": "G333", "name": "균형교양 3영역"},
    {"code": "G344", "name": "균형교양 4영역"},
    {"code": "G355", "name": "균형교양 5영역"},
    {"code": "G19", "name": "일반교양"},
    {"code": "G9", "name": "자율선택"},
]


def _deduplicate_by_code(items: list[dict[str, str]]) -> list[dict[str, str]]:
    unique: dict[str, dict[str, str]] = {}
    for item in items:
        code = str(item.get("code") or "").strip()
        if not code:
            continue
        unique.setdefault(
            code,
            {"code": code, "name": str(item.get("name") or code)},
        )
    return list(unique.values())


def load_search_targets() -> tuple[
    list[dict[str, str]],
    list[dict[str, str]],
    dict[str, str],
]:
    departments = []
    balance_areas = []
    grade_areas: list[dict[str, str]] = []
    if SEARCH_CODES_PATH.exists():
        try:
            payload = json.loads(SEARCH_CODES_PATH.read_text(encoding="utf-8"))
            departments = payload.get("departments", [])
            balance_areas = payload.get("balance_areas", [])
            grade_areas = payload.get("grade_areas", [])
        except (OSError, json.JSONDecodeError):
            pass

    if not departments and DEPARTMENT_CODES_PATH.exists():
        departments = json.loads(DEPARTMENT_CODES_PATH.read_text(encoding="utf-8"))

    departments = _deduplicate_by_code(departments)
    balance_areas = _deduplicate_by_code(balance_areas or FALLBACK_BALANCE_AREAS)
    balance_areas = [
        item for item in balance_areas if item["code"].upper().startswith("G")
    ]

    grade_area_by_grade = dict(DEFAULT_GRADE_AREAS)
    for item in grade_areas:
        code = str(item.get("code") or "").upper()
        if code in {"H1", "H2", "H3", "H4"}:
            grade_area_by_grade[code[1:]] = code

    return departments, balance_areas, grade_area_by_grade


def crawl_all(
    session_cookie: str,
    *,
    year: str,
    semester: str,
    student_number: str,
    student_grade: str,
    student_department_code: str,
    fact_code: str,
    delay_seconds: float = DEFAULT_DELAY_SECONDS,
) -> None:
    departments, balance_areas, grade_area_by_grade = load_search_targets()
    if not departments:
        raise RuntimeError(
            "검색할 학과 코드가 없습니다. crawl_code_all_departments.py를 먼저 실행하세요."
        )
    print(f"전체 전공 수: {len(departments)}개")
    print(f"학년 검색 영역: {grade_area_by_grade}")
    print(f"교양 검색 영역: {[item['code'] for item in balance_areas]}")

    total_courses = 0
    total_saved = 0
    failed = 0
    subject_catalog: dict[str, dict] = {}

    db = SessionLocal()
    try:
        for grade_index, target_grade in enumerate(TARGET_GRADES, start=1):
            target_grade_area = grade_area_by_grade[target_grade]
            print(f"\n===== {target_grade}학년 전공 과목 검색 ({grade_index}/{len(TARGET_GRADES)}) =====")
            for index, department in enumerate(departments, start=1):
                code = department["code"]
                name = department["name"]
                print(f"\n[{target_grade}학년 {index}/{len(departments)}] {name} ({code}) 조회 중...")

                try:
                    courses = crawl_knumis_course_list(
                        session_cookie=session_cookie,
                        year=year,
                        semester=semester,
                        department_code=code,
                        department=name,
                        student_number=student_number,
                        student_grade=student_grade,
                        student_department_code=student_department_code,
                        fact_code=fact_code,
                        # fact_srch는 검색 대상 전공이 아니라 로그인 학생의 소속 학과입니다.
                        fact_srch=student_department_code,
                        grad_srch=target_grade,
                        # 확인된 4학년 POST의 4/H4/H4 조합을 학년별로 맞춥니다.
                        # dept_srch와 dept_code1은 course_crawler에서 모두 code로 전송됩니다.
                        grad_area1=target_grade_area,
                        grad_area2=target_grade_area,
                    )
                    for course in courses:
                        subject_catalog.setdefault(
                            course["subject_code"],
                            {
                                "subject_code": course["subject_code"],
                                "name": course["name"],
                                "department": course.get("department"),
                                "course_type": course.get("course_type"),
                                "semester": course.get("semester") or f"{year}-{semester}",
                            },
                        )
                    saved = save_courses(db, courses)
                    total_courses += len(courses)
                    total_saved += saved
                    print(f"  검색 {len(courses)}개 / 새 분반 저장 {saved}개")
                except Exception as exc:
                    failed += 1
                    print(f"  실패: {exc}")

                if delay_seconds > 0 and index < len(departments):
                    time.sleep(delay_seconds)

            print(f"\n===== {target_grade}학년 교양 과목 검색 =====")
            for index, area in enumerate(balance_areas, start=1):
                code = area["code"]
                name = area["name"]
                print(f"\n[{target_grade}학년 교양 {index}/{len(balance_areas)}] {name} ({code}) 조회 중...")
                try:
                    courses = crawl_knumis_course_list(
                        session_cookie=session_cookie,
                        year=year,
                        semester=semester,
                        department_code="",
                        department=name,
                        student_number=student_number,
                        student_grade=student_grade,
                        student_department_code=student_department_code,
                        fact_code=fact_code,
                        fact_srch=student_department_code,
                        grad_srch=target_grade,
                        grad_area1=code,
                        # grad_area1은 G계열 교양 영역, grad_area2는 대상 학년입니다.
                        grad_area2=target_grade_area,
                    )
                    for course in courses:
                        course["course_type"] = name
                    for course in courses:
                        subject_catalog.setdefault(
                            course["subject_code"],
                            {
                                "subject_code": course["subject_code"],
                                "name": course["name"],
                                "department": course.get("department"),
                                "course_type": course.get("course_type"),
                                "semester": course.get("semester") or f"{year}-{semester}",
                            },
                        )
                    saved = save_courses(db, courses)
                    total_courses += len(courses)
                    total_saved += saved
                    print(f"  검색 {len(courses)}개 / 새 분반 저장 {saved}개")
                except Exception as exc:
                    failed += 1
                    print(f"  실패: {exc}")

                if delay_seconds > 0 and index < len(balance_areas):
                    time.sleep(delay_seconds)
    finally:
        db.close()

    subject_output_path = BACKEND_DIR / "data" / f"subject_codes_{year}-{semester}.json"
    subject_output_path.write_text(
        json.dumps(
            sorted(subject_catalog.values(), key=lambda item: item["subject_code"]),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\n전체 과목 크롤링 완료")
    print(f"검색 과목 수: {total_courses}개")
    print(f"새로 저장된 분반: {total_saved}개")
    print(f"실패 전공: {failed}개")
    print(f"고유 과목 코드: {len(subject_catalog)}개")
    print(f"과목 코드 저장 위치: {subject_output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 6:
        print(
            "사용법: python scripts/crawl_knumis_all_departments.py "
            '"전체 Cookie" 연도 학기 학번 학년 학생학과코드 단과대코드 [지연초]'
        )
        print(
            "예시: python scripts/crawl_knumis_all_departments.py "
            '"JSESSIONID=...; 기타쿠키=..." 2026 2 '
            '202104255 4 5446 5444 1'
        )
        raise SystemExit(1)

    cookie = sys.argv[1]
    target_year = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_YEAR
    target_semester = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_SEMESTER
    student_number = sys.argv[4]
    student_grade = sys.argv[5]
    student_department_code = sys.argv[6] if len(sys.argv) > 6 else ""
    fact_code = sys.argv[7] if len(sys.argv) > 7 else ""
    delay = float(sys.argv[8]) if len(sys.argv) > 8 else DEFAULT_DELAY_SECONDS

    crawl_all(
        cookie,
        year=target_year,
        semester=target_semester,
        student_number=student_number,
        student_grade=student_grade,
        student_department_code=student_department_code,
        fact_code=fact_code,
        delay_seconds=delay,
    )
