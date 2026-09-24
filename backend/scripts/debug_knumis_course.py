"""종합정보 시스템 과목 크롤러 단계별 진단 도구.

쿠키 원문이나 학생 개인정보는 출력하지 않고 응답 상태와 HTML 구조만 확인합니다.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.crawlers.course_crawler import (  # noqa: E402
    KNU_COURSE_SEARCH_PAGE_URL,
    _decode_knumis_response,
    _load_knumis_search_defaults,
    _normalize_session_cookie,
    crawl_course_list_html,
    parse_course_list_html,
)


def debug(session_cookie: str, year: str, semester: str, department_code: str) -> None:
    cookie = _normalize_session_cookie(session_cookie)
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ko,en-US;q=0.9,en;q=0.8",
        "Cookie": cookie,
        "Referer": "https://app.kangnam.ac.kr/knumis/main/main.jsp",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/153.0.0.0 Safari/537.36",
    }

    print("[1] 종합정보 시스템 초기 화면 요청")
    response = requests.get(KNU_COURSE_SEARCH_PAGE_URL, headers=headers, timeout=20)
    html = _decode_knumis_response(response)
    soup = BeautifulSoup(html, "html.parser")
    print(f"  status={response.status_code}, final_url={response.url}")
    print(f"  html_length={len(html)}, title={soup.title.get_text(strip=True) if soup.title else '(없음)'}")
    print(f"  form_count={len(soup.select('form'))}, table_count={len(soup.select('table'))}")
    print(f"  login_markers={{'로그인 후 이용': {'로그인 후 이용' in html}, '세션 만료': {'세션이 만료' in html}}}")
    print(f"  input_names={sorted({x.get('name') for x in soup.select('input[name]') if x.get('name')})}")
    print(f"  select_names={sorted({x.get('name') for x in soup.select('select[name]') if x.get('name')})}")

    print("[2] 초기 검색값 자동 추출")
    defaults = _load_knumis_search_defaults(cookie)
    for key, value in defaults.items():
        # 학번 등 민감할 수 있는 값은 값 자체를 출력하지 않습니다.
        print(f"  {key}: {'설정됨' if value else '(비어 있음)'}")

    print("[3] 과목 검색 POST 요청")
    result_html = crawl_course_list_html(
        session_cookie=cookie,
        year=year,
        semester=semester,
        department_code=department_code,
        student_number=defaults["student_number"],
        student_grade=defaults["student_grade"],
        student_department_code=defaults["student_department_code"],
        fact_code=defaults["fact_code"],
        fact_srch=defaults["fact_srch"] or department_code,
        student_dorn=defaults["student_dorn"],
        grad_srch=defaults["student_grade"],
        dept_code2=defaults["dept_code2"],
        grad_area1=defaults["grad_area1"],
        grad_area2=defaults["grad_area2"],
    )
    result_soup = BeautifulSoup(result_html, "html.parser")
    rows = result_soup.select("table.grid_list tr")
    courses = parse_course_list_html(
        result_html,
        department=department_code,
        semester_override=f"{year}-{semester}",
    )
    body_text = result_soup.get_text(" ", strip=True)
    print(f"  response_length={len(result_html)}")
    print(f"  title={result_soup.title.get_text(strip=True) if result_soup.title else '(없음)'}")
    print(f"  grid_list_rows={len(rows)}, parsed_courses={len(courses)}")
    print(f"  response_markers={{'로그인': {'로그인' in result_html}, '세션 만료': {'세션이 만료' in result_html}}}")
    print(f"  body_preview={body_text[:300]}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "사용법: python scripts/debug_knumis_course.py "
            '"JSESSIONID=..." [연도] [학기] [학과코드]'
        )
        raise SystemExit(1)

    debug(
        sys.argv[1],
        sys.argv[2] if len(sys.argv) > 2 else "2026",
        sys.argv[3] if len(sys.argv) > 3 else "2",
        sys.argv[4] if len(sys.argv) > 4 else "5446",
    )
