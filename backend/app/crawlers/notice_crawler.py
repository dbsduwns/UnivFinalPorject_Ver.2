from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from app.database import SessionLocal
from app.models.notice import Notice
from sqlalchemy.orm import Session
import requests as req
import json
import re
import time

BASE_URL = "https://web.kangnam.ac.kr"
NOTICE_URL = f"{BASE_URL}/menu/f19069e6134f8f8aa7f689a4a675e66f.do"

CATEGORIES = {
   "학사": "116",
   "장학": "117",
   "학습/상담": "118",
   "취창업": "344"
}

def crawl_notice_list(max_items: int | None = None):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        notices = []

        for category_name, menu_seq in CATEGORIES.items():
            url = f"{BASE_URL}/menu/f19069e6134f8f8aa7f689a4a675e66f.do?searchMenuSeq={menu_seq}"

            time.sleep(2)
            
            page = browser.new_page()
            page.goto(url, timeout=120000)
            page.wait_for_selector("a.detailLink")
            
            print(f"현재 URL: {page.url}")
            links = page.query_selector_all("a.detailLink")
            print(f"[{category_name}] 공지 수: {len(links)}")
            
            if links:
                print(f"첫 번째 공지: {links[0].inner_text().strip()}")

            for link in links:
                if max_items is not None and len(notices) >= max_items:
                    break

                title = link.inner_text().strip()
                data_params = json.loads(link.get_attribute("data-params"))
                enc_menu_seq = data_params["encMenuSeq"]
                enc_menu_board_seq = data_params["encMenuBoardSeq"]

                detail_page = browser.new_page()
                try:
                    content, attachment_url = crawl_notice_detail(detail_page, enc_menu_seq, enc_menu_board_seq)
                except Exception as e:
                    print(f"상세 페이지 크롤링 실패(건너뜀): {title[:20]}...-> {e}")
                    content, attachment_url = None, None
                detail_page.close()

                time.sleep(2)

                print(f"제목: {title}")
                print(f"카테고리: {category_name}")
                notices.append({
                    "title": title,
                    "content": content,
                    "category": category_name,
                    "attachment_url": attachment_url
                })

            page.close()

            if max_items is not None and len(notices) >= max_items:
                break

        browser.close()
        return notices
   
def crawl_notice_detail(page, enc_menu_seq, enc_menu_board_seq):
    url = f"https://web.kangnam.ac.kr/menu/board/info/f19069e6134f8f8aa7f689a4a675e66f.do?scrtWrtiYn=false&encMenuSeq={enc_menu_seq}&encMenuBoardSeq={enc_menu_board_seq}"
    page.goto(url, timeout=60000)
    page.wait_for_load_state("networkidle")

    html = page.content()
    soup = BeautifulSoup(html, "html.parser")

    content = soup.select_one("div.tbl_view")
    if content:
        for hidden in content.select(".contents_add_one1, .contents_add_one2"):
            hidden.decompose()

        content_text = content.text.strip()

        if not content_text:
            img = content.select_one("img")
            if img:
                content_text = f"[이미지 공지] {img.get('src')}"

    else:
        content_text = None

    attachment = soup.select_one("a.link_file")
    attachment_url = None
    if attachment:
       href = attachment.get("href")
       attachment_url = f"https://web.kangnam.ac.kr{href}"

    return content_text, attachment_url

def save_notices(notices: list):
   db = SessionLocal()
   try:
        for n in notices:
            existing = db.query(Notice).filter(
                Notice.title == n["title"]
            ).first()
            if existing:
                continue
         
            notice = Notice(
                title=n["title"],
                content=n["content"],
                category=n["category"],
                attachment_url=n["attachment_url"]
            )
            db.add(notice)
        db.commit()
        print("저장 완료!")
   finally:
      db.close()
   

      

if __name__ == "__main__":
    notices = crawl_notice_list()
    save_notices(notices)
