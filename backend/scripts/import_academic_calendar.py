import os
import sys
import json

# 백엔드 최상위 경로를 시스템 패스에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.ai_bot import campus_ai_bot
from langchain_core.documents import Document

def import_calendar():
    print("⏳ 학사일정 데이터를 벡터 DB에 인덱싱 시작...")
    
    # AI 봇 초기화
    campus_ai_bot.initialize()
    
    # PDF에서 추출한 데이터
    calendar_data = [
      { "date": "2026-03-01", "event": "삼일절", "description": "공휴일" },
      { "date": "2026-03-02", "event": "삼일절 대체휴일", "description": "공휴일" },
      { "date": "2026-03-03", "event": "1학기 개강일", "description": "2026학년도 제1학기 수업 시작" },
      { "date": "2026-03-03 ~ 2026-03-09", "event": "1학기 수강신청 변경기간", "description": "제1학기 수강신청 내역 변경 가능 기간" },
      { "date": "2026-03-03 ~ 2026-03-09", "event": "1학기 인정학점취득 신청기간", "description": "" },
      { "date": "2026-03-03 ~ 2026-03-12", "event": "1학기 개강채플", "description": "" },
      { "date": "2026-03-10 ~ 2026-03-30", "event": "1학기 수강 교과목 포기 신청기간", "description": "" },
      { "date": "2026-03-27", "event": "1학기 일반휴학 신청 마감일", "description": "" },
      { "date": "2026-04-20", "event": "개교기념일", "description": "학교 휴무일" },
      { "date": "2026-04-21 ~ 2026-04-27", "event": "1학기 중간시험기간", "description": "" },
      { "date": "2026-05-01", "event": "노동절", "description": "공휴일" },
      { "date": "2026-05-05", "event": "어린이날", "description": "공휴일" },
      { "date": "2026-05-12 ~ 2026-05-14", "event": "목양축전", "description": "강남대학교 축제 기간" },
      { "date": "2026-05-18 ~ 2026-05-22", "event": "전공이수 신청기간", "description": "" },
      { "date": "2026-05-19 ~ 2026-05-20", "event": "전공박람회 기간", "description": "" },
      { "date": "2026-05-18 ~ 2026-05-29", "event": "조기졸업 신청기간", "description": "" },
      { "date": "2026-05-24", "event": "석가탄신일", "description": "공휴일" },
      { "date": "2026-05-25", "event": "석가탄신일 대체휴일", "description": "공휴일" },
      { "date": "2026-06-03", "event": "지방선거", "description": "공휴일" },
      { "date": "2026-06-06", "event": "현충일", "description": "공휴일" },
      { "date": "2026-06-09 ~ 2026-06-15", "event": "1학기 기말시험기간", "description": "" },
      { "date": "2026-06-16 ~ 2026-06-17", "event": "1학기 보강일", "description": "" },
      { "date": "2026-06-18 ~ 2026-07-08", "event": "하계 계절수업기간", "description": "" },
      { "date": "2026-06-18 ~ 2026-06-25", "event": "1학기 강의평가 기간", "description": "" },
      { "date": "2026-06-18 ~ 2026-08-31", "event": "하계방학 기간", "description": "" },
      { "date": "2026-06-22", "event": "1학기 성적제출 마감일", "description": "" },
      { "date": "2026-06-23 ~ 2026-06-25", "event": "1학기 성적확인 및 정정기간", "description": "" },
      { "date": "2026-06-29 ~ 2026-07-08", "event": "2학기 복학 신청기간(1차)", "description": "" },
      { "date": "2026-07-02 ~ 2026-07-16", "event": "2학기 재입학 원서 접수 기간", "description": "" },
      { "date": "2026-07-06 ~ 2026-07-09", "event": "2학기 전부·전과 신청기간", "description": "" },
      { "date": "2026-07-13 ~ 2026-07-16", "event": "2학기 타전공 전공인정 신청 기간", "description": "" },
      { "date": "2026-07-14 ~ 2026-07-15", "event": "2학기 예비수강신청기간", "description": "" },
      { "date": "2026-07-23", "event": "2025학년도 후기 졸업종합사정일", "description": "" },
      { "date": "2026-07-27 ~ 2026-07-29", "event": "학사학위취득 유예 신청기간", "description": "" },
      { "date": "2026-08-04", "event": "2학기 장애학생 선 수강신청일", "description": "" },
      { "date": "2026-08-05 ~ 2026-08-06", "event": "2학기 수강신청기간", "description": "" },
      { "date": "2026-08-15", "event": "광복절", "description": "공휴일" },
      { "date": "2026-08-17", "event": "광복절 대체공휴일", "description": "공휴일" },
      { "date": "2026-08-18 ~ 2026-09-28", "event": "2학기 일반휴학 신청기간", "description": "" },
      { "date": "2026-08-20", "event": "2025학년도 후기 학위수여식", "description": "졸업식" },
      { "date": "2026-08-24 ~ 2026-08-28", "event": "2학기 등록기간", "description": "등록금 납부 기간" },
      { "date": "2026-09-01", "event": "2학기 개강일", "description": "2026학년도 제2학기 수업 시작" },
      { "date": "2026-09-01 ~ 2026-09-07", "event": "2학기 수강신청 변경기간", "description": "" },
      { "date": "2026-09-24 ~ 2026-09-26", "event": "추석연휴", "description": "공휴일" },
      { "date": "2026-10-03", "event": "개천절", "description": "공휴일" },
      { "date": "2026-10-09", "event": "한글날", "description": "공휴일" },
      { "date": "2026-10-20 ~ 2026-10-26", "event": "2학기 중간시험 기간", "description": "" },
      { "date": "2026-12-08 ~ 2026-12-14", "event": "2학기 기말시험 기간", "description": "" },
      { "date": "2026-12-17 ~ 2027-02-28", "event": "동계방학 기간", "description": "" },
      { "date": "2027-01-01", "event": "신정", "description": "공휴일" },
      { "date": "2027-02-06 ~ 2027-02-09", "event": "설연휴 및 대체휴일", "description": "공휴일" },
      { "date": "2027-02-18", "event": "2026학년도 전기 학위수여식", "description": "졸업식" },
      { "date": "2027-03-02", "event": "2027학년도 입학식", "description": "" }
    ]
    
    indexed_docs = []
    for item in calendar_data:
        content = f"날짜: {item['date']}\n행사: {item['event']}"
        if item['description']:
            content += f"\n설명: {item['description']}"
            
        doc = Document(
            page_content=content,
            metadata={
                "source": "학사일정",
                "date": item['date'],
                "event": item['event']
            }
        )
        indexed_docs.append(doc)
    
    if indexed_docs:
        campus_ai_bot.add_documents(indexed_docs)
        print(f"✅ 학사일정 {len(indexed_docs)}개 인덱싱 완료!")

if __name__ == "__main__":
    import_calendar()
