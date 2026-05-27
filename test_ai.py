import os
import asyncio
import time
from dotenv import load_dotenv

# 백엔드 경로 추가
import sys
sys.path.append(os.path.join(os.getcwd(), "backend"))

from backend.app.core.ai_bot import campus_ai_bot

async def test_bot():
    print("🤖 AI Bot 테스트 시작...")
    load_dotenv()
    
    start_time = time.time()
    campus_ai_bot.initialize()
    print(f"✅ 초기화 완료 ({time.time() - start_time:.2f}초)")
    
    question = "6월 학사일정 알려줘"
    print(f"❓ 질문: {question}")
    
    # 1. 질문 재작성 테스트
    print("\n1️⃣ 질문 재작성 중...")
    start_time = time.time()
    rewritten = await campus_ai_bot.rewrite_chain.ainvoke({"question": question})
    print(f"🔄 재작성 결과: {rewritten}")
    print(f"⏱️ 소요 시간: {time.time() - start_time:.2f}초")
    
    # 2. 리트리버 테스트
    print("\n2️⃣ 벡터 DB 검색 중...")
    start_time = time.time()
    docs = await campus_ai_bot.retriever.ainvoke(rewritten)
    print(f"📦 검색된 문서 수: {len(docs)}")
    for i, doc in enumerate(docs):
        print(f"  - Doc {i+1}: {doc.page_content[:50]}...")
    print(f"⏱️ 소요 시간: {time.time() - start_time:.2f}초")
    
    # 3. 전체 체인 테스트
    print("\n3️⃣ 전체 응답 생성 중...")
    start_time = time.time()
    response = await campus_ai_bot.ask(question)
    print(f"✨ 최종 답변: {response[:100]}...")
    print(f"⏱️ 소요 시간: {time.time() - start_time:.2f}초")

if __name__ == "__main__":
    asyncio.run(test_bot())
