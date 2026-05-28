from datetime import date
from app.services.academic_calendar import _infer_query_range, find_academic_events

def test_logic():
    today = date(2026, 5, 28)
    
    # 1. Test "다음 달"
    start, end, upcoming = _infer_query_range("다음 달 학사일정", today)
    print(f"Next month from {today}: {start} to {end}")
    
    # 2. Test Year wraparound (1월 in Dec)
    today_dec = date(2026, 12, 1)
    start, end, upcoming = _infer_query_range("1월 일정", today_dec)
    print(f"Jan query in Dec 2026: {start} to {end}")

    # 3. Test keywords
    from app.services.academic_calendar import is_academic_calendar_query
    print(f"Is '6월 뭐 있어?' academic? {is_academic_calendar_query('6월 뭐 있어?')}")
    print(f"Is '축제 날짜' academic? {is_academic_calendar_query('축제 날짜')}")

if __name__ == "__main__":
    test_logic()
