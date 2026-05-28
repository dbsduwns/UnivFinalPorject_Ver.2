from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta


@dataclass(frozen=True)
class AcademicCalendarEvent:
    start: date
    end: date
    title: str
    description: str = ""

    @property
    def date_text(self) -> str:
        if self.start == self.end:
            return self.start.isoformat()
        return f"{self.start.isoformat()} ~ {self.end.isoformat()}"


ACADEMIC_CALENDAR: list[AcademicCalendarEvent] = [
    AcademicCalendarEvent(date(2026, 3, 1), date(2026, 3, 1), "삼일절", "공휴일"),
    AcademicCalendarEvent(date(2026, 3, 2), date(2026, 3, 2), "삼일절 대체휴일", "공휴일"),
    AcademicCalendarEvent(date(2026, 3, 3), date(2026, 3, 3), "1학기 개강일", "2026학년도 제1학기 수업 시작"),
    AcademicCalendarEvent(date(2026, 3, 3), date(2026, 3, 9), "1학기 수강신청 변경기간", "제1학기 수강신청 내역 변경 가능 기간"),
    AcademicCalendarEvent(date(2026, 3, 3), date(2026, 3, 9), "1학기 인정학점취득 신청기간"),
    AcademicCalendarEvent(date(2026, 3, 3), date(2026, 3, 12), "1학기 개강채플"),
    AcademicCalendarEvent(date(2026, 3, 10), date(2026, 3, 30), "1학기 수강 교과목 포기 신청기간"),
    AcademicCalendarEvent(date(2026, 3, 27), date(2026, 3, 27), "1학기 일반휴학 신청 마감일"),
    AcademicCalendarEvent(date(2026, 4, 20), date(2026, 4, 20), "개교기념일", "학교 휴무일"),
    AcademicCalendarEvent(date(2026, 4, 21), date(2026, 4, 27), "1학기 중간시험기간"),
    AcademicCalendarEvent(date(2026, 5, 1), date(2026, 5, 1), "근로자의 날", "공휴일"),
    AcademicCalendarEvent(date(2026, 5, 5), date(2026, 5, 5), "어린이날", "공휴일"),
    AcademicCalendarEvent(date(2026, 5, 12), date(2026, 5, 14), "목양축전", "강남대학교 축제 기간"),
    AcademicCalendarEvent(date(2026, 5, 18), date(2026, 5, 22), "전공이수 신청기간"),
    AcademicCalendarEvent(date(2026, 5, 19), date(2026, 5, 20), "전공박람회 기간"),
    AcademicCalendarEvent(date(2026, 5, 18), date(2026, 5, 29), "조기졸업 신청기간"),
    AcademicCalendarEvent(date(2026, 5, 24), date(2026, 5, 24), "석가탄신일", "공휴일"),
    AcademicCalendarEvent(date(2026, 5, 25), date(2026, 5, 25), "석가탄신일 대체휴일", "공휴일"),
    AcademicCalendarEvent(date(2026, 6, 3), date(2026, 6, 3), "지방선거", "공휴일"),
    AcademicCalendarEvent(date(2026, 6, 6), date(2026, 6, 6), "현충일", "공휴일"),
    AcademicCalendarEvent(date(2026, 6, 9), date(2026, 6, 15), "1학기 기말시험기간"),
    AcademicCalendarEvent(date(2026, 6, 16), date(2026, 6, 17), "1학기 보강일"),
    AcademicCalendarEvent(date(2026, 6, 18), date(2026, 7, 8), "하계 계절수업기간"),
    AcademicCalendarEvent(date(2026, 6, 18), date(2026, 6, 25), "1학기 강의평가 기간"),
    AcademicCalendarEvent(date(2026, 6, 18), date(2026, 8, 31), "하계방학 기간"),
    AcademicCalendarEvent(date(2026, 6, 22), date(2026, 6, 22), "1학기 성적제출 마감일"),
    AcademicCalendarEvent(date(2026, 6, 23), date(2026, 6, 25), "1학기 성적확인 및 정정기간"),
    AcademicCalendarEvent(date(2026, 6, 29), date(2026, 7, 8), "2학기 복학 신청기간(1차)"),
    AcademicCalendarEvent(date(2026, 7, 2), date(2026, 7, 16), "2학기 재입학 원서 접수 기간"),
    AcademicCalendarEvent(date(2026, 7, 6), date(2026, 7, 9), "2학기 전부·전과 신청기간"),
    AcademicCalendarEvent(date(2026, 7, 13), date(2026, 7, 16), "2학기 타전공 전공인정 신청 기간"),
    AcademicCalendarEvent(date(2026, 7, 14), date(2026, 7, 15), "2학기 예비수강신청기간"),
    AcademicCalendarEvent(date(2026, 7, 23), date(2026, 7, 23), "2025학년도 후기 졸업종합사정일"),
    AcademicCalendarEvent(date(2026, 7, 27), date(2026, 7, 29), "학사학위취득 유예 신청기간"),
    AcademicCalendarEvent(date(2026, 8, 4), date(2026, 8, 4), "2학기 재학생 수강신청일"),
    AcademicCalendarEvent(date(2026, 8, 5), date(2026, 8, 6), "2학기 수강신청기간"),
    AcademicCalendarEvent(date(2026, 8, 15), date(2026, 8, 15), "광복절", "공휴일"),
    AcademicCalendarEvent(date(2026, 8, 17), date(2026, 8, 17), "광복절 대체공휴일", "공휴일"),
    AcademicCalendarEvent(date(2026, 8, 18), date(2026, 9, 28), "2학기 일반휴학 신청기간"),
    AcademicCalendarEvent(date(2026, 8, 20), date(2026, 8, 20), "2025학년도 후기 학위수여일", "졸업일"),
    AcademicCalendarEvent(date(2026, 8, 24), date(2026, 8, 28), "2학기 등록기간", "등록금 납부 기간"),
    AcademicCalendarEvent(date(2026, 9, 1), date(2026, 9, 1), "2학기 개강일", "2026학년도 제2학기 수업 시작"),
    AcademicCalendarEvent(date(2026, 9, 1), date(2026, 9, 7), "2학기 수강신청 변경기간"),
    AcademicCalendarEvent(date(2026, 9, 24), date(2026, 9, 26), "추석연휴", "공휴일"),
    AcademicCalendarEvent(date(2026, 10, 3), date(2026, 10, 3), "개천절", "공휴일"),
    AcademicCalendarEvent(date(2026, 10, 9), date(2026, 10, 9), "한글날", "공휴일"),
    AcademicCalendarEvent(date(2026, 10, 20), date(2026, 10, 26), "2학기 중간시험 기간"),
    AcademicCalendarEvent(date(2026, 12, 8), date(2026, 12, 14), "2학기 기말시험 기간"),
    AcademicCalendarEvent(date(2026, 12, 17), date(2027, 2, 28), "동계방학 기간"),
    AcademicCalendarEvent(date(2027, 1, 1), date(2027, 1, 1), "신정", "공휴일"),
    AcademicCalendarEvent(date(2027, 2, 6), date(2027, 2, 9), "설연휴 및 대체휴일", "공휴일"),
    AcademicCalendarEvent(date(2027, 2, 18), date(2027, 2, 18), "2026학년도 전기 학위수여일", "졸업일"),
    AcademicCalendarEvent(date(2027, 3, 2), date(2027, 3, 2), "2027학년도 입학식"),
]


ACADEMIC_QUERY_KEYWORDS = (
    "학사", "일정", "개강", "방학", "시험", "중간", "기말", "수강",
    "등록", "휴학", "복학", "졸업", "학위", "축제", "목양", "모양", "축전",
    "공휴일", "휴일", "채플", "성적", "전공", "입학식", "언제", "날짜", "달력", "뭐", "행사"
)


def is_academic_calendar_query(question: str) -> bool:
    return any(keyword in question for keyword in ACADEMIC_QUERY_KEYWORDS)


def _topic_keywords(question: str) -> list[str]:
    topics: list[str] = []

    if "기말" in question:
        topics.append("기말시험")
    if "중간" in question:
        topics.append("중간시험")
    if "개강" in question:
        topics.append("개강")
    if "축제" in question or "모양" in question or "목양" in question:
        topics.append("목양축전")
    if "수강" in question:
        topics.append("수강")
    if "등록" in question:
        topics.append("등록")
    if "휴학" in question:
        topics.append("휴학")
    if "복학" in question:
        topics.append("복학")
    if "졸업" in question or "학위" in question:
        topics.extend(["졸업", "학위"])
    if "성적" in question:
        topics.append("성적")

    if "방학" in question:
        if "여름" in question or "하계" in question:
            topics.append("하계방학")
        elif "겨울" in question or "동계" in question:
            topics.append("동계방학")
        else:
            topics.append("방학")

    return topics


def _semester_keywords(question: str) -> list[str]:
    semesters: list[str] = []

    if "1학기" in question or "1 학기" in question:
        semesters.append("1학기")
    if "2학기" in question or "2 학기" in question:
        semesters.append("2학기")

    return semesters


def _month_end(year: int, month: int) -> date:
    if month == 12:
        return date(year, 12, 31)
    return date(year, month + 1, 1) - timedelta(days=1)


def _current_week(today: date) -> tuple[date, date]:
    start = today - timedelta(days=today.weekday())
    return start, start + timedelta(days=6)


def _infer_query_range(question: str, today: date) -> tuple[date, date, bool]:
    if "내일" in question:
        target = today + timedelta(days=1)
        return target, target, False

    if "오늘" in question:
        return today, today, False

    if "다음 주" in question or "다음주" in question:
        start, _ = _current_week(today)
        start += timedelta(days=7)
        return start, start + timedelta(days=6), False

    if "이번 주" in question or "이번주" in question:
        start, end = _current_week(today)
        return start, end, False

    year_match = re.search(r"(20\d{2})\s*년", question)
    if year_match:
        year = int(year_match.group(1))
        if "1학기" in question or "1 학기" in question:
            return date(year, 3, 1), date(year, 8, 31), False
        if "2학기" in question or "2 학기" in question:
            return date(year, 9, 1), date(year + 1, 2, 28), False
        return date(year, 1, 1), date(year, 12, 31), False

    iso_match = re.search(r"(20\d{2})[-./년 ]\s*(\d{1,2})[-./월 ]\s*(\d{1,2})", question)
    if iso_match:
        target = date(int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3)))
        return target, target, False

    month_day_match = re.search(r"(\d{1,2})\s*월\s*(\d{1,2})\s*일", question)
    if month_day_match:
        target = date(today.year, int(month_day_match.group(1)), int(month_day_match.group(2)))
        return target, target, False

    # 월 단위 검색 (6월, 12월 등)
    month_match = re.search(r"(\d{1,2})\s*월", question)
    if month_match:
        month = int(month_match.group(1))
        if 1 <= month <= 12:
            year = today.year
            # 만약 요청한 월이 현재 월보다 많이 앞서고(예: 현재 12월인데 1월 요청), 
            # 올해 해당 월 일정이 없다면 내년으로 가정
            if month < today.month - 1 and today.month >= 10:
                year += 1
            return date(year, month, 1), _month_end(year, month), False

    if "다음 달" in question or "다음달" in question:
        year = today.year
        month = today.month + 1
        if month > 12:
            month = 1
            year += 1
        return date(year, month, 1), _month_end(year, month), False

    if "저번 달" in question or "저번달" in question:
        year = today.year
        month = today.month - 1
        if month < 1:
            month = 12
            year -= 1
        return date(year, month, 1), _month_end(year, month), False

    if "이번 달" in question or "이번달" in question:
        return date(today.year, today.month, 1), _month_end(today.year, today.month), False

    return today, date(today.year + 1, today.month, today.day), True


def _overlaps(event: AcademicCalendarEvent, start: date, end: date) -> bool:
    return event.start <= end and event.end >= start


def find_academic_events(question: str, today: date | None = None, limit: int = 15) -> list[AcademicCalendarEvent]:
    if today is None:
        today = datetime.now().date()

    start, end, upcoming_only = _infer_query_range(question, today)
    topics = _topic_keywords(question)
    semesters = _semester_keywords(question)

    if upcoming_only:
        events = [event for event in ACADEMIC_CALENDAR if event.end >= today]
    else:
        events = [event for event in ACADEMIC_CALENDAR if _overlaps(event, start, end)]

    if topics:
        topic_events = [
            event
            for event in events
            if any(topic in event.title or topic in event.description for topic in topics)
        ]
        if topic_events:
            events = topic_events

    if semesters:
        semester_events = [
            event
            for event in events
            if any(semester in event.title or semester in event.description for semester in semesters)
        ]
        if semester_events:
            events = semester_events

    return sorted(events, key=lambda event: (event.start, event.end, event.title))[:limit]


def build_academic_calendar_answer(question: str, today: date | None = None) -> str:
    if today is None:
        today = datetime.now().date()

    if not is_academic_calendar_query(question):
        return ""

    events = find_academic_events(question, today=today)
    if not events:
        return "해당 조건에 맞는 학사일정을 찾지 못했어요."

    lines = ["학사일정 기준으로 확인해보면 다음과 같아요."]
    for event in events:
        description = f" ({event.description})" if event.description else ""
        lines.append(f"- {event.date_text}: {event.title}{description}")

    return "\n".join(lines)


def build_academic_calendar_context(question: str, today: date | None = None) -> str:
    if today is None:
        today = datetime.now().date()

    if not is_academic_calendar_query(question):
        return ""

    events = find_academic_events(question, today=today)
    if not events:
        return (
            "[구조화된 학사일정]\n"
            f"기준일: {today.isoformat()}\n"
            "질문 조건에 해당하는 학사일정을 찾지 못했습니다."
        )

    lines = [
        "[구조화된 학사일정]",
        f"기준일: {today.isoformat()}",
        "아래 일정은 날짜 범위 계산으로 조회한 결과입니다. 학사일정 질문에는 이 목록을 우선 근거로 사용하세요.",
    ]
    for event in events:
        description = f" - {event.description}" if event.description else ""
        lines.append(f"- {event.date_text}: {event.title}{description}")
    return "\n".join(lines)
