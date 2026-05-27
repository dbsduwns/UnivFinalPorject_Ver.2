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

async def test_today_schedule():
    print("📅 [테스트] '오늘 일정 뭐야?' 질문 테스트 시작...")
    campus_ai_bot.initialize()
    
    query = "오늘 일정 뭐야?"
    print(f"\n👤 질문: {query}")
    
    try:
        response = await campus_ai_bot.ask(query)
        print(f"🤖 AI 답변:\n{response}")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    asyncio.run(test_today_schedule())
