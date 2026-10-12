from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from bs4 import BeautifulSoup
from bs4.element import NavigableString


ACADEMIC_CALENDAR_URL = (
    "https://web.kangnam.ac.kr/menu/02be162adc07170ec7ee034097d627e9.do"
)

_YEAR_MONTH_PATTERN = re.compile(
    r"(?P<year>20\d{2})\s*(?:[.]|년\s*)\s*(?P<month>1[0-2]|0?[1-9])(?:\s*월)?"
)
_DATE_PATTERN = re.compile(
    r"^\s*(?P<start_month>1[0-2]|0?[1-9])[.]"
    r"(?P<start_day>0?[1-9]|[12]\d|3[01])(?:\([^)]*\))?"
    r"(?:\s*[~∼～-]\s*"
    r"(?P<end_month>1[0-2]|0?[1-9])[.]"
    r"(?P<end_day>0?[1-9]|[12]\d|3[01])(?:\([^)]*\))?)?\s*$"
)


@dataclass(frozen=True)
class CrawledAcademicCalendarEvent:
    start: date
    end: date
    title: str
    calendar_year: int
    source_url: str = ACADEMIC_CALENDAR_URL

    @property
    def date_text(self) -> str:
        if self.start == self.end:
            return self.start.isoformat()
        return f"{self.start.isoformat()} ~ {self.end.isoformat()}"

    @property
    def stable_id(self) -> str:
        return f"academic-calendar:{self.start}:{self.end}:{self.title}"


def _clean_text(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())


def _closest_year_month(table, default_year: int) -> tuple[int, int | None]:
    for heading in table.find_all_previous(["h1", "h2", "h3", "h4", "h5", "h6"], limit=20):
        match = _YEAR_MONTH_PATTERN.search(_clean_text(heading.get_text(" ", strip=True)))
        if match:
            return int(match.group("year")), int(match.group("month"))
    for previous_element in table.previous_elements:
        if not isinstance(previous_element, NavigableString):
            continue
        match = _YEAR_MONTH_PATTERN.search(_clean_text(str(previous_element)))
        if match:
            return int(match.group("year")), int(match.group("month"))
    return default_year, None


def _year_nearest_to_section(month: int, section_year: int, section_month: int) -> int:
    difference = month - section_month
    if difference > 6:
        return section_year - 1
    if difference < -6:
        return section_year + 1
    return section_year


def _parse_date_range(
    value: str,
    *,
    section_year: int,
    section_month: int | None,
) -> tuple[date, date] | None:
    match = _DATE_PATTERN.fullmatch(_clean_text(value))
    if not match:
        return None

    start_month = int(match.group("start_month"))
    start_day = int(match.group("start_day"))
    end_month = int(match.group("end_month") or start_month)
    end_day = int(match.group("end_day") or start_day)

    if section_month is None:
        start_year = section_year
    else:
        start_year = _year_nearest_to_section(start_month, section_year, section_month)

    end_year = start_year
    if section_month is not None:
        end_year = _year_nearest_to_section(end_month, section_year, section_month)

    start = date(start_year, start_month, start_day)
    end = date(end_year, end_month, end_day)
    if end < start:
        end = date(end_year + 1, end_month, end_day)
    return start, end


def parse_academic_calendar_html(
    html: str,
    *,
    default_year: int | None = None,
    source_url: str = ACADEMIC_CALENDAR_URL,
) -> list[CrawledAcademicCalendarEvent]:
    """Parse every undergraduate academic-calendar row from the official page."""

    soup = BeautifulSoup(html, "html.parser")
    page_text = _clean_text(soup.get_text(" ", strip=True))
    if "접근이 차단되었습니다" in page_text or "Access Restricted" in page_text:
        raise RuntimeError("강남대학교 홈페이지가 크롤링 요청을 차단했습니다.")

    if default_year is None:
        year_match = re.search(r"(20\d{2})\s*년도\s*학사일정", page_text)
        default_year = int(year_match.group(1)) if year_match else datetime.now().year

    events: dict[tuple[date, date, str], CrawledAcademicCalendarEvent] = {}
    for table in soup.find_all("table"):
        section_year, section_month = _closest_year_month(table, default_year)
        for row in table.find_all("tr"):
            cells = row.find_all(["th", "td"])
            if len(cells) < 2:
                continue

            raw_date = _clean_text(cells[0].get_text(" ", strip=True))
            parsed_range = _parse_date_range(
                raw_date,
                section_year=section_year,
                section_month=section_month,
            )
            if parsed_range is None:
                continue

            title = _clean_text(cells[-1].get_text(" ", strip=True))
            if not title or title.isdigit():
                continue

            start, end = parsed_range
            key = (start, end, title)
            events[key] = CrawledAcademicCalendarEvent(
                start=start,
                end=end,
                title=title,
                calendar_year=section_year,
                source_url=source_url,
            )

    return sorted(events.values(), key=lambda item: (item.start, item.end, item.title))


def crawl_academic_calendar(
    *,
    url: str = ACADEMIC_CALENDAR_URL,
    default_year: int | None = None,
    max_retries: int = 3,
) -> list[CrawledAcademicCalendarEvent]:
    """Load the official calendar with a browser and parse all displayed rows."""

    from playwright.sync_api import sync_playwright

    last_error: Exception | None = None
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            context = browser.new_context(
                locale="ko-KR",
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()
            for attempt in range(1, max_retries + 1):
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
                    page.wait_for_timeout(2_000)
                    events = parse_academic_calendar_html(
                        page.content(),
                        default_year=default_year,
                        source_url=url,
                    )
                    if not events:
                        raise RuntimeError("공식 페이지에서 학사일정 행을 찾지 못했습니다.")
                    return events
                except Exception as exc:
                    last_error = exc
                    if attempt < max_retries:
                        time.sleep(attempt * 3)
        finally:
            browser.close()

    raise RuntimeError(f"학사일정 크롤링에 실패했습니다: {last_error}")


def parse_academic_calendar_file(
    path: str | Path,
    *,
    default_year: int | None = None,
) -> list[CrawledAcademicCalendarEvent]:
    html = Path(path).read_text(encoding="utf-8")
    return parse_academic_calendar_html(html, default_year=default_year)
