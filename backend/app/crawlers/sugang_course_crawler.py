from __future__ import annotations

import json
import shutil
import subprocess
from urllib.parse import urlencode

from app.crawlers.course_crawler import parse_schedule_text


KNU_SUGANG_COURSE_LIST_URL = "https://sugang.kangnam.ac.kr/d/c/lectList"


class SugangCourseCrawlError(RuntimeError):
    """Raised when the course-registration site does not return course JSON."""


def crawl_sugang_course_list(
    *,
    session_cookie: str,
    semester: str,
    category: str,
    area: str = "",
    department_code: str = "",
    grade: str = "",
    dorn: str = "1",
    keyword: str = "",
    course_type: str | None = None,
    timeout: int = 20,
) -> list[dict]:
    """Fetch one filtered course-registration list and normalize its rows.

    The registration site exposes only its currently active registration term.
    ``semester`` is deliberately supplied by the caller so that the snapshot is
    stored under the term being crawled rather than inferred from a URL that
    does not contain year or semester parameters.
    """
    form_data = {
        "pCategory": category,
        "pArea": area,
        "pDorn": dorn,
        "pLectNm": keyword,
    }
    if department_code:
        form_data["pDeptCd"] = department_code
    if grade:
        form_data["pGrade"] = grade

    curl_command = shutil.which("curl.exe") or shutil.which("curl")
    if not curl_command:
        raise SugangCourseCrawlError("수강신청 사이트 연결에 필요한 curl을 찾을 수 없습니다.")

    try:
        completed = subprocess.run(
            [
                curl_command,
                "--silent",
                "--show-error",
                "--location",
                "--request",
                "POST",
                KNU_SUGANG_COURSE_LIST_URL,
                "--header",
                "Accept: application/json, text/javascript, */*; q=0.01",
                "--header",
                "Accept-Language: ko,en-US;q=0.9,en;q=0.8",
                "--header",
                "Content-Type: application/x-www-form-urlencoded; charset=UTF-8",
                "--header",
                "Origin: https://sugang.kangnam.ac.kr",
                "--header",
                "Referer: https://sugang.kangnam.ac.kr/",
                "--header",
                "X-Requested-With: XMLHttpRequest",
                "--header",
                (
                    "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/153.0.0.0 Safari/537.36"
                ),
                "--cookie",
                session_cookie,
                "--data-raw",
                urlencode(form_data),
                "--max-time",
                str(timeout),
            ],
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise SugangCourseCrawlError(
            "수강신청 사이트 연결 프로그램을 실행하지 못했습니다."
        ) from exc

    if completed.returncode != 0:
        raise SugangCourseCrawlError(
            "수강신청 서버 연결에 실패했습니다. 잠시 후 다시 시도하세요."
        )

    try:
        payload = json.loads(completed.stdout.decode("utf-8"))
    except json.JSONDecodeError as exc:
        # Invalid sessions return an HTML logout page with status 200.
        raise SugangCourseCrawlError(
            "수강신청 사이트가 강좌 JSON 대신 로그인/로그아웃 페이지를 반환했습니다. "
            "JSESSIONID와 KN_SUGANG_SESSION을 포함한 새 Cookie 헤더가 필요합니다."
        ) from exc

    if isinstance(payload, dict) and str(payload.get("code")) in {"999", "login"}:
        raise SugangCourseCrawlError(payload.get("message") or "수강신청 세션이 만료되었습니다.")

    rows = _extract_rows(payload)
    return [
        _normalize_course(row, semester=semester, category=category, course_type=course_type)
        for row in rows
    ]


def _extract_rows(payload: object) -> list[dict]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]

    if not isinstance(payload, dict):
        raise SugangCourseCrawlError("수강신청 강좌 목록의 응답 형식이 예상과 다릅니다.")

    for key in ("data", "rows"):
        rows = payload.get(key)
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
        if isinstance(rows, dict):
            for nested_key in ("data", "rows"):
                nested_rows = rows.get(nested_key)
                if isinstance(nested_rows, list):
                    return [row for row in nested_rows if isinstance(row, dict)]

    raise SugangCourseCrawlError("수강신청 강좌 목록 응답에서 data/rows를 찾지 못했습니다.")


def _normalize_course(
    row: dict,
    *,
    semester: str,
    category: str,
    course_type: str | None = None,
) -> dict:
    subject_code = _text(row.get("SUBJ_NUMB"))
    section = _text(row.get("LCTR_CLAS"))
    name = _text(row.get("SUBJ_NM"))
    if not subject_code or not section or not name:
        raise SugangCourseCrawlError("강좌 목록에 학수번호, 분반 또는 과목명이 없는 행이 있습니다.")

    schedule_text = _text(row.get("TIME_VIEW"))
    return {
        "subject_code": subject_code,
        "section": section,
        "name": name,
        "professor": _text(row.get("EMPL_KNAM")) or None,
        "credits": _to_int(row.get("SUBJ_UNIT")),
        "hours": _to_int(row.get("HIS_TM")),
        "schedule_text": schedule_text,
        "semester": semester,
        "department": _text(row.get("DEPT_KNAM")) or None,
        "course_type": course_type or ("교양" if category == "17" else "전공" if category == "1" else None),
        "schedules": parse_schedule_text(schedule_text),
    }


def _text(value: object) -> str:
    return "" if value is None else str(value).strip()


def _to_int(value: object) -> int:
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return 0
