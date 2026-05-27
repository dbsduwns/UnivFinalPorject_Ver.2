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
    학교 서버 부하를 최소화하면서 모든 공지사항을 수집하는 개선된 크롤러입니다 (V3).
    본문 내 포함된 이미지 URL도 함께 추출합니다.
    """
    db = SessionLocal()
    try:
        # DB에 이미 저장된 모든 공지사항 제목을 가져옵니다.
        titles = db.query(Notice.title).all()
        saved_titles = {t[0] for t in titles}
        print(f"이미 저장된 공지 수: {len(saved_titles)}개")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            page = context.new_page()

            for category_name, menu_seq in CATEGORIES.items():
                print(f"\n🚀 [{category_name}] 카테고리 수집 시작 (V3)...")
                
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

                    new_items = []
                    for link in links:
                        title = link.inner_text().strip()
                        # 이미 저장된 제목이거나 이번 실행에서 방금 저장한 제목이면 건너뜁니다.
                        if title in saved_titles:
                            continue
                        
                        data_params = json.loads(link.get_attribute("data-params"))
                        new_items.append({
                            "title": title,
                            "encMenuSeq": data_params["encMenuSeq"],
                            "encMenuBoardSeq": data_params["encMenuBoardSeq"]
                        })

                    if not new_items:
                        print("  ✨ 이 페이지의 모든 공지가 이미 DB에 있습니다.")
                        # 한 페이지 전체가 이미 있다면 다음 카테고리로 넘어가거나 종료할 수도 있지만,
                        # 공지사항 순서가 섞일 수 있으므로 continue로 다음 페이지를 확인합니다.
                        continue

                    print(f"  🆕 {len(new_items)}개의 새로운 공지 발견. 상세 내용 수집 중...")
                    
                    for item in new_items:
                        # 한 번 더 개별적으로 중복 체크 (세션 내 중복 방지)
                        if item["title"] in saved_titles:
                            continue

                        content, attachment_url, published_at = crawl_detail(page, item["encMenuSeq"], item["encMenuBoardSeq"])
                        
                        if content:
                            try:
                                # 즉시 DB 저장 및 RAG 인덱싱
                                notice = Notice(
                                    title=item["title"],
                                    content=content,
                                    category=category_name,
                                    attachment_url=attachment_url,
                                    published_at=published_at
                                )
                                db.add(notice)
                                db.commit()
                                
                                # RAG 인덱싱
                                doc = Document(
                                    page_content=f"제목: {item['title']}\n카테고리: {category_name}\n내용: {content}",
                                    metadata={
                                        "source": "공지사항",
                                        "category": category_name,
                                        "title": item["title"]
                                    }
                                )
                                campus_ai_bot.add_documents([doc])
                                
                                # 캐시 업데이트
                                saved_titles.add(item["title"])
                                print(f"    ✅ 수집 및 저장 완료: {item['title'][:30]}... ({published_at})")
                            except Exception as e:
                                print(f"    ❌ DB 저장 중 오류 발생 ({item['title'][:20]}): {e}")
                                db.rollback()
                        
                        time.sleep(random.uniform(1.0, 2.5))

                    time.sleep(random.uniform(2.0, 4.0))

            browser.close()
    finally:
        db.close()

def crawl_detail(page, enc_menu_seq, enc_menu_board_seq):
    """상세 페이지에서 본문(텍스트+이미지), 첨부파일 링크, 작성일을 추출합니다."""
    url = f"https://web.kangnam.ac.kr/menu/board/info/f19069e6134f8f8aa7f689a4a675e66f.do?scrtWrtiYn=false&encMenuSeq={enc_menu_seq}&encMenuBoardSeq={enc_menu_board_seq}"
    
    try:
        page.goto(url, timeout=30000)
        page.wait_for_load_state("networkidle")
        
        html = page.content()
        soup = BeautifulSoup(html, "html.parser")

        # 1. 작성일(published_at) 추출
        published_at = None
        date_div = soup.select_one(".tblw_date")
        if date_div:
            # "등록날짜\n2026.05.19 11:28 조회수..." 형태에서 날짜 부분 추출
            date_text = date_div.get_text(separator=" ", strip=True)
            import re
            # 정규식으로 YYYY.MM.DD HH:MM 형식 추출
            match = re.search(r'(\d{4}\.\d{2}\.\d{2}\s\d{2}:\d{2})', date_text)
            if match:
                # DB 저장을 위해 YYYY-MM-DD HH:MM:SS 형식으로 변환 시도
                try:
                    from datetime import datetime
                    dt = datetime.strptime(match.group(1), "%Y.%m.%d %H:%M")
                    published_at = dt.isoformat()
                except ValueError:
                    published_at = None

        content_div = soup.select_one("div.tbl_view")
        content_text = ""
        if content_div:
            # 불필요한 요소 제거
            for hidden in content_div.select(".contents_add_one1, .contents_add_one2"):
                hidden.decompose()
            
            # 본문 내 이미지 추출
            images = content_div.select("img")
            image_urls = []
            for img in images:
                src = img.get("src")
                if src:
                    if not src.startswith("http"):
                        src = f"{BASE_URL}{src}"
                    image_urls.append(src)
            
            # 텍스트 추출
            text_part = content_div.get_text(separator="\n", strip=True)
            
            # 이미지 정보 결합
            if image_urls:
                img_tags = "\n".join([f"[이미지] {url}" for url in image_urls])
                if not text_part:
                    # 텍스트가 없고 이미지만 있는 경우
                    content_text = "\n".join([f"[이미지 공지] {url}" for url in image_urls])
                else:
                    # 텍스트와 이미지가 섞인 경우 (하단에 이미지 링크 추가)
                    content_text = f"{text_part}\n\n{img_tags}"
            else:
                content_text = text_part
        
        attachment = soup.select_one("a.link_file")
        attachment_url = None
        if attachment:
            href = attachment.get("href")
            attachment_url = f"{BASE_URL}{href}"

        return content_text, attachment_url, published_at
    except Exception as e:
        print(f"    ❌ 상세 페이지 로드 실패: {e}")
        return None, None, None

def save_to_db_and_rag(notices: list):
    """수집된 공지사항을 DB에 저장합니다."""
    db = SessionLocal()
    indexed_docs = []
    try:
        for n in notices:
            existing = db.query(Notice).filter(Notice.title == n["title"]).first()
            if existing:
                continue
                
            notice = Notice(
                title=n["title"],
                content=n["content"],
                category=n["category"],
                attachment_url=n["attachment_url"],
                published_at=n.get("published_at")
            )
            db.add(notice)
            
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
    print("🌟 본문 내 이미지 수집이 강화된 크롤러(V3)를 시작합니다.")
    # 테스트를 위해 3페이지 정도만 수집
    crawl_notices_safely(max_pages=5)
