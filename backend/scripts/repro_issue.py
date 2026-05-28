import asyncio
import os
from datetime import date, datetime
from dotenv import load_dotenv

# Mocking the bot's dependencies to test logic without full LLM if needed, 
# but here we can try the full bot since we have the environment.
from app.core.ai_bot import CampusAIBot
from app.services.academic_calendar import (
    build_academic_calendar_context,
    is_academic_calendar_query,
    find_academic_events,
    _infer_query_range
)

load_dotenv()

async def diagnose():
    question = "6월 학사일정 알려줘"
    today = date(2026, 5, 28) # As per session context
    
    print(f"--- Diagnosing: '{question}' (Today: {today}) ---")
    
    # 1. Check keyword matching
    is_academic = is_academic_calendar_query(question)
    print(f"Is academic query: {is_academic}")
    
    # 2. Check range inference
    start, end, upcoming_only = _infer_query_range(question, today)
    print(f"Inferred range: {start} to {end} (upcoming_only={upcoming_only})")
    
    # 3. Check event finding
    events = find_academic_events(question, today=today)
    print(f"Found {len(events)} events in calendar service.")
    for e in events:
        print(f"  - {e.start} ~ {e.end}: {e.title}")
        
    # 4. Check context building
    academic_context = build_academic_calendar_context(question, today=today)
    print(f"Academic Context length: {len(academic_context)}")
    print(f"Academic Context preview: {academic_context[:100]}...")

    # 5. Full Bot Test (requires GOOGLE_API_KEY)
    if os.getenv("GOOGLE_API_KEY"):
        print("\n--- Running full bot logic ---")
        bot = CampusAIBot()
        bot.initialize()
        
        # Test Query Rewrite
        rewritten = await bot.rewrite_chain.ainvoke({"question": question})
        print(f"Rewritten Question: {rewritten}")
        
        # Test Vector DB retrieval
        if bot.retriever:
            docs = await bot.retriever.ainvoke(rewritten or question)
            print(f"Vector DB retrieved {len(docs)} documents.")
            for i, d in enumerate(docs):
                print(f"  [{i}] Source: {d.metadata.get('source')}, Title: {d.metadata.get('title') or d.metadata.get('event')}")
        
        # Test full build_context
        # Note: bot.build_context uses datetime.now() internally, which might differ from our 'today'
        # Let's see what it does.
        context = await bot.build_context(question, rewritten)
        print(f"Final Context length: {len(context)}")
        if "정보가 없습니다" in context:
            print("⚠️ WARNING: Context contains 'No information found' message.")
        
        # Test LLM response
        response = await bot.ask(question)
        print(f"AI Response:\n{response}")
    else:
        print("\nSkipping full bot test (GOOGLE_API_KEY missing)")

if __name__ == "__main__":
    asyncio.run(diagnose())
