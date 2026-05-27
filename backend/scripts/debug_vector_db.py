import os
import sys
from pathlib import Path

# backend 폴더를 path에 추가
backend_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(backend_dir))

from app.core.ai_bot import campus_ai_bot
from dotenv import load_dotenv

# .env 로드
load_dotenv(backend_dir / ".env")

def debug_vector_db():
    print("🔍 [디버그] 벡터 DB 상태 확인 중...")
    campus_ai_bot.initialize()
    
    if not campus_ai_bot.vectorstore:
        print("❌ 벡터 스토어가 로드되지 않았습니다.")
        return

    # 1. "학사일정" 소스로 검색 시도
    results = campus_ai_bot.vectorstore.similarity_search("학사일정", k=10)
    print(f"\n📌 '학사일정' 검색 결과 ({len(results)}개):")
    for i, doc in enumerate(results):
        print(f"--- 결과 {i+1} ---")
        print(f"Metadata: {doc.metadata}")
        print(f"Content: {doc.page_content[:100]}...")

    # 2. 특정 이벤트 검색 시도
    results = campus_ai_bot.vectorstore.similarity_search("목양축전", k=5)
    print(f"\n📌 '목양축전' 검색 결과 ({len(results)}개):")
    for i, doc in enumerate(results):
        print(f"--- 결과 {i+1} ---")
        print(f"Metadata: {doc.metadata}")
        print(f"Content: {doc.page_content[:100]}...")

if __name__ == "__main__":
    debug_vector_db()
