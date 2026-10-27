"""Extract a university academic-calendar PDF into a versioned JSON seed file."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

import pdfplumber


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PDF_PATH = PROJECT_ROOT / "2026학년도 학사일정_3차.pdf"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "backend" / "data" / "academic_calendar_seed.json"
DATE_RANGE_PATTERN = re.compile(
    r"(?P<start_month>\d{2})\.(?P<start_day>\d{2})\([월화수목금토일]\)"
    r"(?:\s*[~∼]\s*(?P<end_month>\d{2})\.(?P<end_day>\d{2})\([월화수목금토일]\))?"
)


@dataclass(frozen=True)
class CalendarEvent:
    title: str
    start_date: str
    end_date: str
    source_page: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract an academic-calendar PDF to a JSON seed file.")
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--academic-year", type=int, help="Defaults to the first 'YYYY학년도' in the PDF.")
    parser.add_argument("--dry-run", action="store_true", help="Print events but do not write the seed file.")
    return parser.parse_args()


def clean_cell(value: str | None) -> str:
    return " ".join((value or "").split())


def read_academic_year(pdf: pdfplumber.PDF) -> int:
    for page in pdf.pages:
        matched = re.search(r"(20\d{2})\s*학년도", page.extract_text() or "")
        if matched:
            return int(matched.group(1))
    raise ValueError("PDF에서 'YYYY학년도' 표기를 찾지 못했습니다.")


def split_aligned_cells(dates: str, descriptions: str, *, page_number: int) -> Iterable[tuple[str, str]]:
    date_lines = [line.strip() for line in dates.splitlines() if line.strip()]
    description_lines = [line.strip() for line in descriptions.splitlines() if line.strip()]
    if len(date_lines) != len(description_lines):
        raise ValueError(
            f"{page_number}쪽의 일정({len(date_lines)}개)과 내용({len(description_lines)}개)이 일치하지 않습니다."
        )
    return zip(date_lines, description_lines, strict=True)


def calendar_year_for_month(academic_year: int, month: int) -> int:
    """January and February normally belong to the following calendar year."""
    return academic_year + 1 if month in (1, 2) else academic_year


def parse_event(date_text: str, title: str, *, academic_year: int, page_number: int) -> CalendarEvent:
    matched = DATE_RANGE_PATTERN.fullmatch(clean_cell(date_text))
    if not matched:
        raise ValueError(f"{page_number}쪽의 일정 날짜 형식을 해석하지 못했습니다: {date_text!r}")
    start_month = int(matched["start_month"])
    end_month = int(matched["end_month"]) if matched["end_month"] else start_month
    start = date(calendar_year_for_month(academic_year, start_month), start_month, int(matched["start_day"]))
    end = (
        date(
            # A range such as 02.11~03.29 belongs entirely to the next
            # calendar year; a range such as 12.17~01.08 crosses into it.
            academic_year + 1 if start.year == academic_year + 1 or end_month < start_month else academic_year,
            end_month,
            int(matched["end_day"]),
        )
        if matched["end_month"]
        else start
    )
    if end < start:
        raise ValueError(f"{page_number}쪽의 종료일이 시작일보다 빠릅니다: {date_text!r}")
    normalized_title = clean_cell(title)
    if not normalized_title:
        raise ValueError(f"{page_number}쪽에 내용이 없는 일정이 있습니다: {date_text!r}")
    return CalendarEvent(normalized_title, start.isoformat(), end.isoformat(), page_number)


def extract_events(pdf_path: Path, academic_year: int | None = None) -> tuple[int, list[CalendarEvent]]:
    with pdfplumber.open(pdf_path) as pdf:
        resolved_year = academic_year or read_academic_year(pdf)
        events: list[CalendarEvent] = []
        for page_number, page in enumerate(pdf.pages, start=1):
            for table in page.extract_tables():
                for row in table:
                    if len(row) < 10 or not row[8] or not row[9]:
                        continue
                    # Skip the table header ("일정" / "내용") while retaining
                    # strict validation for actual schedule rows.
                    if not re.match(r"\s*\d{2}\.\d{2}\(", row[8]):
                        continue
                    for date_text, title in split_aligned_cells(row[8], row[9], page_number=page_number):
                        events.append(parse_event(date_text, title, academic_year=resolved_year, page_number=page_number))
    if not events:
        raise ValueError("PDF에서 학사일정 행을 추출하지 못했습니다.")
    return resolved_year, sorted(events, key=lambda event: (event.start_date, event.end_date, event.title))


def build_seed(pdf_path: Path, academic_year: int, events: list[CalendarEvent]) -> dict:
    return {
        "schema_version": 1,
        "academic_year": academic_year,
        "source_document": {
            "filename": pdf_path.name,
            "sha256": hashlib.sha256(pdf_path.read_bytes()).hexdigest(),
        },
        "events": [asdict(event) for event in events],
    }


def main() -> None:
    args = parse_args()
    pdf_path = args.pdf.resolve()
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")
    academic_year, events = extract_events(pdf_path, args.academic_year)
    seed = build_seed(pdf_path, academic_year, events)
    if args.dry_run:
        print(json.dumps(seed, ensure_ascii=False, indent=2))
        return
    output_path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(seed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"학사일정 seed 생성 완료: {output_path} ({len(events)}개 일정)")


if __name__ == "__main__":
    main()
