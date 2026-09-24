import sys
import os

# 백엔드 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.crawlers.course_crawler import save_courses
from app.crawlers.sugang_course_crawler import (
    SugangCourseCrawlError,
    crawl_sugang_course_list,
)

DEFAULT_SEMESTER = "2026-2"

# 수강신청 시스템의 전체 조회 조건. 이 시스템은 현재 수강신청 학기만
# 노출하므로, 학기 값은 실행 시 명시적으로 붙여 DB 스냅샷을 만든다.
CRAWL_TARGETS = [
    {"label": "전공 전체", "category": "1", "course_type": "전공"},
    {
        "label": "균형교양 1영역",
        "category": "17",
        "area": "31",
        "course_type": "균형교양 1영역",
    },
    {
        "label": "균형교양 2영역",
        "category": "17",
        "area": "32",
        "course_type": "균형교양 2영역",
    },
    {
        "label": "균형교양 3영역",
        "category": "17",
        "area": "33",
        "course_type": "균형교양 3영역",
    },
    {
        "label": "균형교양 4영역",
        "category": "17",
        "area": "345",
        "course_type": "균형교양 4영역",
    },
    {
        "label": "균형교양 5영역",
        "category": "17",
        "area": "35",
        "course_type": "균형교양 5영역",
    },
]


def crawl_all_departments(session_cookie: str, semester: str = DEFAULT_SEMESTER) -> None:
    if "KN_SUGANG_SESSION=" not in session_cookie or "JSESSIONID=" not in session_cookie:
        print("❌ 수강신청 사이트의 전체 Cookie 헤더가 필요합니다 (JSESSIONID, KN_SUGANG_SESSION 포함).")
        return

    db = SessionLocal()
    total_saved = 0
    
    try:
        for target in CRAWL_TARGETS:
            try:
                items = crawl_sugang_course_list(
                    session_cookie=session_cookie,
                    semester=semester,
                    category=target["category"],
                    area=target.get("area", ""),
                    course_type=target["course_type"],
                )
                saved = save_courses(db, items)
                total_saved += saved
                print(f"✅ {target['label']}: {len(items)}개 과목 발견 (새 분반 {saved}개)")
            except SugangCourseCrawlError as exc:
                print(f"❌ {target['label']} 조회 실패: {exc}")

        print(f"\n✨ {semester} 수강신청 강좌 수집 완료! 새 분반 {total_saved}개")

    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python scripts/crawl_all_departments.py \"수강신청_COOKIE_전체값\" [학기]")
        print("예시: python scripts/crawl_all_departments.py \"JSESSIONID=...; KN_SUGANG_SESSION=...\" 2026-2")
    else:
        cookie = sys.argv[1]
        target_semester = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_SEMESTER
        crawl_all_departments(cookie, target_semester)
