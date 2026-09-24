"""종합정보 시스템의 최신 전공·교양 검색 코드를 수집합니다.

이 스크립트는 과목 목록(sbr3070L.jsp)을 조회하지 않습니다.
검색 화면(sbr3070T.jsp)의 select 옵션을 읽어 다음 JSON을 생성합니다.

backend/data/knumis_search_codes.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.crawlers.course_crawler import (  # noqa: E402
    KNU_COURSE_SEARCH_PAGE_URL,
    _decode_knumis_response,
    _normalize_session_cookie,
)

OUTPUT_PATH = BACKEND_DIR / "data" / "knumis_search_codes.json"
LEGACY_DEPARTMENT_PATH = BACKEND_DIR / "data" / "department_codes_all.json"

SEARCH_FIELD_NAMES = (
    "dept_srch",
    "dept_code1",
    "dept_code2",
    "grad_srch",
    "grad_area1",
    "grad_area2",
)


def extract_options(soup: BeautifulSoup, *field_names: str) -> list[dict[str, str]]:
    select = None
    for field_name in field_names:
        select = soup.select_one(
            f"select[name='{field_name}'], select#{field_name}"
        )
        if select:
            break
    if not select:
        return []

    options = []
    for option in select.select("option"):
        code = str(option.get("value") or "").strip()
        name = option.get_text(" ", strip=True)
        if code:
            options.append({"code": code, "name": name or code})
    return options


def deduplicate_options(options: list[dict[str, str]]) -> list[dict[str, str]]:
    """같은 코드가 여러 번 나타나도 첫 번째 표시명만 유지합니다."""
    unique: dict[str, dict[str, str]] = {}
    for option in options:
        unique.setdefault(option["code"], option)
    return list(unique.values())


def extract_search_field_options(soup: BeautifulSoup) -> dict[str, list[dict[str, str]]]:
    """의미를 추측하지 않고 검색 관련 select 옵션을 필드별로 보존합니다."""
    return {
        field_name: deduplicate_options(extract_options(soup, field_name))
        for field_name in SEARCH_FIELD_NAMES
    }


def extract_search_field_values(soup: BeautifulSoup) -> dict[str, str]:
    """검색 필드의 현재 선택값만 저장합니다(학번·세션 정보 제외)."""
    values: dict[str, str] = {}
    for field_name in SEARCH_FIELD_NAMES:
        element = soup.select_one(f"[name='{field_name}'], #{field_name}")
        if not element:
            values[field_name] = ""
            continue
        if element.name == "select":
            selected = element.select_one("option[selected]")
            if selected is None:
                selected = element.select_one("option")
            values[field_name] = str(selected.get("value") or "").strip() if selected else ""
        else:
            values[field_name] = str(element.get("value") or "").strip()
    return values


def crawl_search_codes(
    session_cookie: str,
    *,
    year: str,
    semester: str,
    student_number: str,
) -> dict:
    cookie = _normalize_session_cookie(session_cookie)
    session = requests.Session()
    common_headers = {
        "Accept-Language": "ko,en-US;q=0.9,en;q=0.8",
        "Cookie": cookie,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154.0.0.0 Safari/537.36",
    }

    # 브라우저의 실제 진입 순서와 동일하게 세션 초기화 페이지를 먼저 방문합니다.
    session.get(
        "https://app.kangnam.ac.kr/knumis/main/main.jsp",
        headers={**common_headers, "Referer": "https://app.kangnam.ac.kr/"},
        timeout=20,
    ).raise_for_status()
    session.get(
        "https://app.kangnam.ac.kr/knumis/sbr/sbr3070S.jsp",
        headers={**common_headers, "Referer": "https://app.kangnam.ac.kr/knumis/main/main.jsp"},
        timeout=20,
    ).raise_for_status()

    response = session.post(
        KNU_COURSE_SEARCH_PAGE_URL,
        headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ko,en-US;q=0.9,en;q=0.8",
            "Cache-Control": "max-age=0",
            "Content-Type": "application/x-www-form-urlencoded",
            "Cookie": cookie,
            "Origin": "https://app.kangnam.ac.kr",
            "Referer": "https://app.kangnam.ac.kr/knumis/sbr/sbr3070S.jsp",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154.0.0.0 Safari/537.36",
        },
        data={
            "schl_year": year,
            "schl_smst": semester,
            "stnt_numb": student_number,
        },
        timeout=20,
    )
    response.raise_for_status()
    html = _decode_knumis_response(response)
    soup = BeautifulSoup(html, "html.parser")

    if len(html) < 1000 or not soup.select("select[name]"):
        raise RuntimeError(
            "검색 코드 화면을 받지 못했습니다. 전체 Cookie가 유효한지 확인하세요."
        )

    raw_options = extract_search_field_options(soup)
    raw_values = extract_search_field_values(soup)

    # 실제 검색 POST에서 dept_srch와 dept_code1에는 같은 대상 학과 코드가
    # 전달되었습니다. dept_srch 옵션을 우선 사용하되, 구형 화면에서 해당
    # select가 없을 때만 dept_code1/dept_code를 대체 목록으로 사용합니다.
    department_source_field = "dept_srch"
    departments = raw_options["dept_srch"]
    if not departments:
        department_source_field = "dept_code1"
        departments = raw_options["dept_code1"]
    if not departments:
        department_source_field = "dept_code"
        departments = deduplicate_options(extract_options(soup, "dept_code"))

    # stnt_dept는 로그인 학생의 소속이므로 검색 대상 학과 목록으로 사용하지 않습니다.
    grade_area_options = raw_options["grad_area1"]
    if not grade_area_options:
        grade_area_options = deduplicate_options(extract_options(soup, "grad_area"))
    grade_areas = [
        option
        for option in grade_area_options
        if option["code"].upper() in {"H1", "H2", "H3", "H4"}
    ]
    balance_areas = [
        option
        for option in grade_area_options
        if option["code"].upper().startswith("G")
    ]

    if not departments and not balance_areas:
        select_names = sorted(
            {
                str(element.get("name") or element.get("id"))
                for element in soup.select("select")
                if element.get("name") or element.get("id")
            }
        )
        input_names = sorted(
            {
                str(element.get("name"))
                for element in soup.select("input[name]")
            }
        )
        preview = soup.get_text(" ", strip=True)[:200]
        raise RuntimeError(
            "검색 코드 옵션을 찾지 못했습니다. "
            f"select={select_names}, inputs={input_names}, preview={preview!r}"
        )

    result = {
        "year": year,
        "semester": semester,
        "departments": departments,
        "department_source_field": department_source_field,
        "grade_areas": grade_areas,
        "balance_areas": balance_areas,
        # 다음 분석 때 dept_code1/2 등을 서로 섞지 않도록 원본 select 옵션을
        # 필드별로 저장합니다. 학번·쿠키 같은 개인정보는 포함하지 않습니다.
        "raw_options": raw_options,
        "raw_values": raw_values,
        "source": KNU_COURSE_SEARCH_PAGE_URL,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 기존 전체 전공 크롤러와의 호환을 위해 전공 목록도 갱신합니다.
    if departments:
        LEGACY_DEPARTMENT_PATH.write_text(
            json.dumps(departments, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return result


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print(
            "사용법: python scripts/crawl_code_all_departments.py "
            '"전체 Cookie" 연도 학기 학번'
        )
        print(
            "예시: python scripts/crawl_code_all_departments.py "
            '"JSESSIONID=...; 기타쿠키=..." 2026 2 202104255'
        )
        raise SystemExit(1)

    result = crawl_search_codes(
        sys.argv[1],
        year=sys.argv[2],
        semester=sys.argv[3],
        student_number=sys.argv[4],
    )
    print(f"전공 코드: {len(result['departments'])}개")
    print(f"전공 코드 출처 필드: {result['department_source_field']}")
    print(f"학년 영역 코드: {len(result['grade_areas'])}개")
    print(f"교양 영역 코드: {len(result['balance_areas'])}개")
    print(f"저장 위치: {OUTPUT_PATH}")
