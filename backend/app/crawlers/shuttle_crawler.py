from email.message import Message
from urllib.parse import urljoin, unquote
from app.database import SessionLocal
from app.models.shuttle import Shuttle
from app.core.ai_bot import campus_ai_bot
from app.core.notification import notify_users_by_type_sync
from langchain_core.documents import Document
import re

import os
import requests
from bs4 import BeautifulSoup

#학교 셔틀 페이지
SHUTTLE_PAGE_URL = "https://web.kangnam.ac.kr/menu/4990be9bdd4defbf92dde49a31ad1a3b.do"
STATIC_SHUTTLE_DIR = "static/shuttle"

#크롤링 함수 메인
def crawl_shuttle_schedule() -> dict:
    os.makedirs(STATIC_SHUTTLE_DIR, exist_ok=True)
    
    page_response = requests.get(
        SHUTTLE_PAGE_URL,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=20,
    )
    page_response.raise_for_status()

    soup = BeautifulSoup(page_response.text, "html.parser")
    download_url = _find_download_url(soup)

    file_response = requests.get(
        download_url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": SHUTTLE_PAGE_URL,
        },
        timeout=20,
        stream=True,
    )
    file_response.raise_for_status()

    original_filename = _extract_filename(
        file_response.headers.get("Content-Disposition")
    )
    
    # 로컬에 파일 저장 (한글 파일명으로 인한 인코딩 이슈 방지를 위해 안전한 이름 사용)
    import time
    timestamp = int(time.time())
    safe_filename = f"shuttle_schedule_{timestamp}.pdf"
        
    local_file_path = os.path.join(STATIC_SHUTTLE_DIR, safe_filename)
    
    with open(local_file_path, "wb") as f:
        for chunk in file_response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    file_response.close()

    semester = _extract_semester(original_filename)

    return {
        "title": _make_title(original_filename),
        "semester": semester,
        "file_url": f"/static/shuttle/{safe_filename}", # 로컬 상대 경로로 저장
        "source_url": SHUTTLE_PAGE_URL,
        "original_filename": original_filename,
    }

#BeautifulSoup를 이용해 다운로드 링크 찾기
def _find_download_url(soup: BeautifulSoup) -> str:
    for a in soup.select("a"):
        text = a.get_text(strip=True)
        href = a.get("href")

        if not href:
            continue

        if "다운로드" in text or "/comm/cmnFile/download.do" in href:
            return urljoin(SHUTTLE_PAGE_URL, href)

    raise ValueError("셔틀 시간표 다운로드 링크를 찾을 수 없습니다.")

# Headers를 이용해 파일 이름 추출
def _extract_filename(content_disposition: str | None) -> str | None:
    if not content_disposition:
        return None

    try:
        content_disposition = content_disposition.encode('iso-8859-1').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass

    match = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', content_disposition)
    if not match:
        return None

    filename = match.group(1)
    return unquote(filename, encoding="utf-8")

# filename에서 학기 추출
def _extract_semester(filename: str | None) -> str | None:
    if not filename:
        return None

    match = re.search(r"(\d{4})\s*[-년]\s*([12])\s*학기", filename)
    if not match:
        return None

    return f"{match.group(1)}-{match.group(2)}"

# filename에서 제목 추출
def _make_title(filename: str | None) -> str:
    if not filename:
        return "순환버스 운행시간표"

    return filename.rsplit(".", 1)[0]

def save_shuttle_schedule(schedule):
    db = SessionLocal()
    try:
        # 1. 중복 체크: 동일한 학기/제목의 데이터가 있는지 확인
        existing = db.query(Shuttle).filter(
            Shuttle.title == schedule["title"],
            Shuttle.semester == schedule["semester"]
        ).first()
        
        if existing:
            print(f"이미 존재하는 시간표입니다: {schedule['title']}")
            return

        # 2. 기존의 활성화된 시간표들을 비활성(0)으로 변경 (버전 관리)
        db.query(Shuttle).filter(Shuttle.is_active == 1).update({"is_active": 0})

        # 3. 새로운 셔틀 데이터 객체 생성 (전달받은 schedule 딕셔너리 값 사용)
        shuttle_schedule = Shuttle(
            title=schedule["title"],
            semester=schedule["semester"],
            file_url=schedule["file_url"],
            source_url=schedule["source_url"],
            original_filename=schedule["original_filename"],
            is_active=1
        )
        db.add(shuttle_schedule)
        db.commit()

        # 4. RAG 인덱싱: AI가 사용자에게 친절하게 링크를 안내할 수 있도록 구성
        page_content = (
            f"강남대학교 셔틀버스 운행 시간표 안내\n"
            f"학기: {schedule['semester']}\n"
            f"공지 제목: {schedule['title']}\n"
            f"운행 시간표 파일 다운로드 링크: {schedule['file_url']}\n"
            f"설명: 이 정보는 {schedule['semester']} 학기의 셔틀버스 전체 운행 시간표를 포함한 파일 링크입니다. "
            f"상세한 첫차, 막차 및 배차 간격은 위 링크의 파일을 다운로드하여 확인하시기 바랍니다."
        )
        
        doc = Document(
            page_content=page_content,
            metadata={
                "source": "셔틀시간표",
                "semester": schedule["semester"],
                "type": "transport",
                "url": schedule["file_url"]
            }
        )

        # 벡터 DB에 리스트 형태로 추가
        campus_ai_bot.add_documents([doc])
        
        # 푸시 알림 전송
        notify_users_by_type_sync(
            db, 
            "shuttle_alert", 
            "🚌 셔틀버스 시간표 업데이트", 
            f"[{schedule['semester']}] 새로운 셔틀버스 시간표가 등록되었습니다."
        )

        print(f"✅ [{schedule['semester']}] {schedule['title']} 저장 및 인덱싱 완료!")
    except Exception as e:
        print(f"❌ 저장 중 오류 발생: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    shuttle_schedule = crawl_shuttle_schedule()
    save_shuttle_schedule(shuttle_schedule)

