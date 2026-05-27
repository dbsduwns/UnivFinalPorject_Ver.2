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

async def test_today_debug():
    print("📅 [테스트] '오늘 일정 뭐야?' 디버그 시작...")
    campus_ai_bot.initialize()
    
    question = "오늘 일정 뭐야?"
    print(f"\n👤 질문: {question}")
    
    # 1. Rewritten question
    rewritten_question = await campus_ai_bot.rewrite_chain.ainvoke({"question": question})
    print(f"🔄 재작성된 질문: {rewritten_question}")
    
    # 2. Retrieved documents
    docs = campus_ai_bot.retriever.invoke(rewritten_question)
    print(f"\n📌 검색된 문서 ({len(docs)}개):")
    for i, doc in enumerate(docs):
        print(f"--- 결과 {i+1} ---")
        print(f"Metadata: {doc.metadata}")
        print(f"Content: {doc.page_content}")
    
    # 3. Final answer
    response = await campus_ai_bot.ask(question)
    print(f"\n🤖 AI 답변:\n{response}")

if __name__ == "__main__":
    asyncio.run(test_today_debug())
