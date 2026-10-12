from datetime import date

from app.crawlers.academic_calendar_crawler import parse_academic_calendar_html
from scripts.sync_academic_calendar import build_document


SAMPLE_HTML = """
<html><body>
  <h2>2026년도 학사일정</h2>
  <section>
    <h3>2026.01 January</h3>
    <table>
      <tr><th>날짜</th><th>일정내용</th></tr>
      <tr><td>12.15(월)~01.06(화)</td><td>계절수업기간</td></tr>
      <tr><td>01.13(화)</td><td>성적표조회기간</td></tr>
    </table>
  </section>
  <section>
    <h3>2026.12 December</h3>
    <table>
      <tr><th>날짜</th><th>일정내용</th></tr>
      <tr><td>12.17(목)~02.28(일)</td><td>동계방학기간</td></tr>
      <tr><td>12.17(목)~02.28(일)</td><td>동계방학기간</td></tr>
    </table>
  </section>
</body></html>
"""


def test_parse_all_rows_and_cross_year_ranges():
    events = parse_academic_calendar_html(SAMPLE_HTML)
    by_title = {event.title: event for event in events}

    assert len(events) == 3
    assert by_title["계절수업기간"].start == date(2025, 12, 15)
    assert by_title["계절수업기간"].end == date(2026, 1, 6)
    assert by_title["동계방학기간"].start == date(2026, 12, 17)
    assert by_title["동계방학기간"].end == date(2027, 2, 28)


def test_qdrant_document_contains_date_metadata():
    event = next(
        event
        for event in parse_academic_calendar_html(SAMPLE_HTML)
        if event.title == "성적표조회기간"
    )
    document = build_document(event)

    assert document.metadata["source"] == "학사일정"
    assert document.metadata["start_date"] == "2026-01-13"
    assert document.metadata["end_date"] == "2026-01-13"
    assert document.metadata["academic_year"] == 2026
    assert document.metadata["source_url"].startswith("https://web.kangnam.ac.kr/")
    assert "시작일: 2026-01-13" in document.page_content
