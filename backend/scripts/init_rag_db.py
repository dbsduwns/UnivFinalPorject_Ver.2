import os
import sys

# 백엔드 최상위 경로를 시스템 패스에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.notice import Notice
from app.core.ai_bot import campus_ai_bot
from langchain_core.documents import Document

def init_db():
    print("⏳ 기존 데이터를 벡터 DB에 인덱싱 시작...")
    
    # AI 봇 초기화
    campus_ai_bot.initialize()
    
    db: Session = SessionLocal()
    try:
        # 1. 공지사항 인덱싱
        notices = db.query(Notice).all()
        print(f"📦 총 {len(notices)}개의 공지사항을 처리 중...")
        
        indexed_docs = []
        for n in notices:
            if n.content:
                doc = Document(
                    page_content=f"제목: {n.title}\n카테고리: {n.category}\n내용: {n.content}",
                    metadata={
                        "source": "공지사항",
                        "category": n.category,
                        "title": n.title
                    }
                )
                indexed_docs.append(doc)
        
        if indexed_docs:
            campus_ai_bot.add_documents(indexed_docs)
            print(f"✅ 공지사항 {len(indexed_docs)}개 인덱싱 완료!")

        # 2. 기타 학사일정/학칙 등 추가 데이터가 있다면 여기에 작성
        # 예: 
        # documents = [Document(page_content="졸업학점은 130학점입니다.", metadata={"source": "학칙"})]
        # campus_ai_bot.add_documents(documents)

    finally:
        db.close()
    
    print("✨ 모든 인덱싱 작업이 완료되었습니다!")

if __name__ == "__main__":
    init_db()
