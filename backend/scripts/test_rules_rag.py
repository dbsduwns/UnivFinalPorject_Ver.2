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

async def test_rules_query():
    print("🚀 대학 규정 기반 RAG 테스트를 시작합니다...")
    
    # AI Bot 초기화 (비동기 처리를 위해 필요시 호출)
    # campus_ai_bot.initialize() 는 첫 ask 호출 시 자동으로 실행됨
    
    test_queries = [
        "장학금을 받으려면 직전 학기에 몇 학점 이상 이수해야 해?",
        "졸업을 하려면 총 몇 학점을 채워야 하니?",
        "계절수업은 한 학기에 최대 몇 학점까지 들을 수 있어?",
        "편입생의 경우 학점 인정은 어떻게 이루어져?",
        "학칙 시행세칙에 따르면 휴학 기간은 어떻게 돼?"
    ]

    for query in test_queries:
        print(f"\n👤 질문: {query}")
        print("⏳ 답변 생성 중...")
        
        response = await campus_ai_bot.ask(query)
        
        print(f"🤖 AI 답변:\n{response}")
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(test_rules_query())
