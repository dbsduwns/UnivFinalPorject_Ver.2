import json
import sys
import os
import time

# 백엔드 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.crawlers.course_crawler import crawl_department_courses, save_courses

def crawl_all_departments(session_cookie):
    # 1. 학과 코드 로드
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, "..", "data", "department_codes_all.json")
    
    if not os.path.exists(json_path):
        print(f"❌ 에러: {json_path} 파일이 없습니다.")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        all_departments = json.load(f)

    # 2. 크롤링 설정
    YEAR = "2026"
    SEMESTER = "1"
    STUDENT_INFO = {
        "student_number": "202104255",
        "student_grade": "4",
        "student_department_code": "5446",
        "fact_code": "5444", 
        "fact_srch": "5446"
    }

    # 학년 및 교양 영역 정의
    MAJOR_GRADES = ["H1", "H2", "H3", "H4"]
    LIBERAL_AREAS = ["G31", "G32", "G333", "G344", "G355", "G9", "G19"]

    db = SessionLocal()
    total_saved = 0
    
    try:
        for i, dept in enumerate(all_departments):
            dept_code = dept["code"]
            dept_name = dept["name"]
            
            # 교양, 원격, 학점교류 학과는 교양 영역(G) 순회
            if dept_code in ["5185", "5183", "5181"]:
                target_areas = LIBERAL_AREAS
                is_liberal = True
            else:
                target_areas = MAJOR_GRADES
                is_liberal = False

            print(f"[{i+1}/{len(all_departments)}] {dept_name} ({dept_code}) 시작...")

            for area in target_areas:
                area_label = "교양영역" if is_liberal else "학년"
                print(f"   🔍 {area_label} {area} 조회 중...", end="\r")
                
                # 교양(G계열) 조회 시에는 학과 코드를 비워야 전체 조회가 가능함
                current_dept = dept if not is_liberal else {"code": "", "name": dept_name}

                try:
                    results = crawl_department_courses(
                        session_cookie=session_cookie,
                        year=YEAR,
                        semester=SEMESTER,
                        departments=[current_dept],
                        **STUDENT_INFO,
                        grad_area1=area,
                        delay_seconds=0.6
                    )
                    
                    for res in results:
                        if res["parsed_count"] > 0:
                            saved = save_courses(db, res["items"])
                            total_saved += saved
                            print(f"   ✅ {area_label} {area}: {res['parsed_count']}개 과목 발견 (저장 {saved}개)")
                
                except Exception as e:
                    print(f"   ❌ {area} 처리 중 오류: {e}")

            # 학과 하나 끝날 때마다 커밋
            db.commit()

        print(f"\n✨ 모든 작업 완료! 총 {total_saved}개의 강의 정보가 업데이트되었습니다.")

    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python scripts/crawl_all_departments.py \"SESSION_COOKIE\"")
    else:
        cookie = sys.argv[1]
        crawl_all_departments(cookie)
