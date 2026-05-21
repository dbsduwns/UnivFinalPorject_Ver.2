import os
import sys
import asyncio
from pathlib import Path

# backend 폴더를 path에 추가
backend_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(backend_dir))

from app.core.ai_bot import campus_ai_bot
from dotenv import load_dotenv

# .env 로드
load_dotenv(backend_dir / ".env")

async def verify_calendar():
    print("📅 [검증] 학사일정 데이터 검색 테스트를 시작합니다...")
    
    # AI Bot 초기화 (첫 실행 시 모델 다운로드로 인해 시간이 걸릴 수 있음)
    print("🤖 AI 엔진 초기화 중... (첫 실행 시 1~2분 소요될 수 있습니다)")
    
    test_queries = [
        "2026년 1학기 개강일이 언제야?",
        "목양축전 기간 알려줘",
        "여름방학은 언제부터 시작하니?",
        "2027년 입학식 날짜 알려줘"
    ]

    for query in test_queries:
        print(f"\n👤 질문: {query}")
        print("⏳ 검색 및 답변 생성 중...")
        
        try:
            response = await campus_ai_bot.ask(query)
            print(f"🤖 AI 답변:\n{response}")
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(verify_calendar())
