import os
import sys
import time
import json
import random
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from pathlib import Path

# backend 폴더를 path에 추가
backend_dir = Path(__file__).resolve().parents[2]
sys.path.append(str(backend_dir))

from app.database import SessionLocal
from app.models.notice import Notice
from app.core.ai_bot import campus_ai_bot
from langchain_core.documents import Document

BASE_URL = "https://web.kangnam.ac.kr"
NOTICE_URL = f"{BASE_URL}/menu/f19069e6134f8f8aa7f689a4a675e66f.do"

CATEGORIES = {
    "학사": "116",
    "장학": "117",
    "학습/상담": "118",
    "취창업": "344"
}

def get_saved_titles():
    """DB에 이미 저장된 모든 공지사항 제목을 가져옵니다."""
    db = SessionLocal()
    try:
        # 제목만 가져와서 set으로 변환 (검색 속도 향상)
        titles = db.query(Notice.title).all()
        return {t[0] for t in titles}
    finally:
        db.close()

def crawl_notices_safely(max_pages: int = 1000):
    """
    학교 서버 부하를 최소화하면서 모든 공지사항을 수집하는 개선된 크롤러입니다.
    1. DB에 이미 있는 공지는 상세 페이지를 요청하지 않습니다.
    2. 단일 브라우저 탭을 재사용하여 자원을 절약합니다.
    3. 랜덤 지연 시간을 추가하여 서버 차단을 방지합니다.
    """
    saved_titles = get_saved_titles()
    print(f"이미 저장된 공지 수: {len(saved_titles)}개")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        page = context.new_page()

        for category_name, menu_seq in CATEGORIES.items():
            print(f"\n🚀 [{category_name}] 카테고리 수집 시작...")
            
            for page_no in range(1, max_pages + 1):
                url = f"{NOTICE_URL}?searchMenuSeq={menu_seq}&paginationInfo.currentPageNo={page_no}"
                print(f"  📄 페이지 {page_no} 분석 중: {url}")
                
                try:
                    page.goto(url, timeout=60000)
                    page.wait_for_selector("a.detailLink", timeout=10000)
                except Exception as e:
                    print(f"  ⚠️ 페이지 로드 실패 또는 공지 없음 (종료): {e}")
                    break

                links = page.query_selector_all("a.detailLink")
                if not links:
                    print("  ⚠️ 더 이상 공지사항이 없습니다.")
                    break

                # 이번 페이지에서 새로 수집할 공지만 골라내기
                new_items = []
                for link in links:
                    title = link.inner_text().strip()
                    if title in saved_titles:
                        continue
                    
                    data_params = json.loads(link.get_attribute("data-params"))
                    new_items.append({
                        "title": title,
                        "encMenuSeq": data_params["encMenuSeq"],
                        "encMenuBoardSeq": data_params["encMenuBoardSeq"]
                    })

                if not new_items:
                    print("  ✨ 이 페이지의 모든 공지가 이미 DB에 있습니다. 다음 페이지로 넘어갑니다.")
                    # 만약 1페이지부터 순차적으로 수집 중이라면 여기서 해당 카테고리를 종료해도 됨
                    # 하지만 중간에 누락된 게 있을 수 있으니 계속 진행하거나, 
                    # 연속으로 N개 이상 중복이면 멈추는 로직을 넣을 수 있음.
                    continue

                print(f"  🆕 {len(new_items)}개의 새로운 공지 발견. 상세 내용 수집 중...")
                
                notices_to_save = []
                for item in new_items:
                    # 상세 페이지 수집
                    content, attachment_url = crawl_detail(page, item["encMenuSeq"], item["encMenuBoardSeq"])
                    
                    if content:
                        notices_to_save.append({
                            "title": item["title"],
                            "content": content,
                            "category": category_name,
                            "attachment_url": attachment_url
                        })
                        print(f"    ✅ 수집 완료: {item['title'][:30]}...")
                    
                    # 서버 부하 방지를 위한 랜덤 지연 (1~2.5초)
                    time.sleep(random.uniform(1.0, 2.5))

                # 한 페이지 분량씩 저장
                if notices_to_save:
                    save_to_db_and_rag(notices_to_save)
                
                # 페이지 전환 전 지연
                time.sleep(random.uniform(2.0, 4.0))

        browser.close()

def crawl_detail(page, enc_menu_seq, enc_menu_board_seq):
    """상세 페이지에서 본문과 첨부파일 링크를 추출합니다."""
    url = f"https://web.kangnam.ac.kr/menu/board/info/f19069e6134f8f8aa7f689a4a675e66f.do?scrtWrtiYn=false&encMenuSeq={enc_menu_seq}&encMenuBoardSeq={enc_menu_board_seq}"
    
    try:
        page.goto(url, timeout=30000)
        page.wait_for_load_state("networkidle")
        
        html = page.content()
        soup = BeautifulSoup(html, "html.parser")

        content_div = soup.select_one("div.tbl_view")
        content_text = ""
        if content_div:
            # 불필요한 요소 제거 (예: 비밀번호 입력창 등)
            for hidden in content_div.select(".contents_add_one1, .contents_add_one2"):
                hidden.decompose()
            
            content_text = content_div.get_text(separator="\n", strip=True)
            
            # 텍스트가 없고 이미지만 있는 경우 처리
            if not content_text:
                img = content_div.select_one("img")
                if img:
                    content_text = f"[이미지 공지] {img.get('src')}"
        
        attachment = soup.select_one("a.link_file")
        attachment_url = None
        if attachment:
            href = attachment.get("href")
            attachment_url = f"{BASE_URL}{href}"

        return content_text, attachment_url
    except Exception as e:
        print(f"    ❌ 상세 페이지 로드 실패: {e}")
        return None, None

def save_to_db_and_rag(notices: list):
    """수집된 공지사항을 DB에 저장하고 벡터 DB에 인덱싱합니다."""
    db = SessionLocal()
    indexed_docs = []
    try:
        for n in notices:
            # 최종 중복 체크 (동시 실행 방지)
            existing = db.query(Notice).filter(Notice.title == n["title"]).first()
            if existing:
                continue
                
            notice = Notice(
                title=n["title"],
                content=n["content"],
                category=n["category"],
                attachment_url=n["attachment_url"]
            )
            db.add(notice)
            
            # RAG 인덱싱용 문서 생성
            doc = Document(
                page_content=f"제목: {n['title']}\n카테고리: {n['category']}\n내용: {n['content']}",
                metadata={
                    "source": "공지사항",
                    "category": n["category"],
                    "title": n["title"]
                }
            )
            indexed_docs.append(doc)

        db.commit()
        
        if indexed_docs:
            campus_ai_bot.add_documents(indexed_docs)
            print(f"  💾 {len(indexed_docs)}개 공지 저장 및 인덱싱 완료")
            
    except Exception as e:
        print(f"  ❌ DB 저장 중 오류 발생: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("🌟 개선된 안전 공지사항 크롤러(V2)를 시작합니다.")
    # 각 카테고리별로 최근 20페이지씩만 수집하도록 설정 변경
    crawl_notices_safely(max_pages=20)
