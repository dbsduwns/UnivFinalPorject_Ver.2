import sys
import os
from sqlalchemy import func

# 백엔드 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.subject import Subject
from app.models.course import Course

def verify_db_stats():
    db = SessionLocal()
    try:
        # 1. 전체 강의(분반 포함) 수
        total_courses = db.query(Course).count()
        # 2. 전체 과목(학수번호 기준) 수
        total_subjects = db.query(Subject).count()
        
        print(f"📊 [DB 통계 요약]")
        print(f"   - 전체 과목 수: {total_subjects}개")
        print(f"   - 전체 강의(분반) 수: {total_courses}개")
        print("-" * 40)

        # 3. 학과별 강의 수 (상위 20개)
        print("📍 [학과별 수집 현황 - 상위 20개]")
        stats = db.query(Subject.department, func.count(Course.id)) \
                  .join(Course, Subject.id == Course.subject_id) \
                  .group_by(Subject.department) \
                  .order_by(func.count(Course.id).desc()) \
                  .limit(20).all()
        
        for dept, count in stats:
            print(f"   - {dept or '소속미정'}: {count}개")
        
        print("-" * 40)
        
        # 4. 수집된 데이터가 0개인 학과 수 확인
        # (이건 나중에 department_codes_all.json과 비교 필요)
        
    finally:
        db.close()

if __name__ == "__main__":
    verify_db_stats()
