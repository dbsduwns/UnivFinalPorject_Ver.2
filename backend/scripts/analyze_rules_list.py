import os
import sys
import time
import re
from playwright.sync_api import sync_playwright
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(backend_dir))

from dotenv import load_dotenv
load_dotenv(backend_dir / ".env")

def login(page):
    knu_user_id = os.getenv("KNU_USER_ID")
    knu_password = os.getenv("KNU_PASSWORD")
    if not knu_user_id or not knu_password:
        raise RuntimeError("KNU_USER_ID 및 KNU_PASSWORD가 .env 파일에 설정되어 있지 않습니다.")

    print("🔐 로그인 시도 중...")
    page.goto("https://nsso.kangnam.ac.kr/sso/auth?response_type=code&client_id=HOMEPAGE&redirect_uri=https://web.kangnam.ac.kr/nsso/login_proc.jsp")
    page.fill("input[name='user_id']", knu_user_id)
    page.fill("input[name='pw']", knu_password)
    page.click("button[type='submit']")
    page.wait_for_load_state("networkidle")
    print("✅ 로그인 완료")

def analyze_list():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            login(page)
            print("🚀 목록 페이지 접속...")
            page.goto("https://app.kangnam.ac.kr/knumis/mo_open/rulesL1.jsp?rglt_cont2=&rglt_cont=&gubn=&save_gubn=")
            page.wait_for_load_state("networkidle")
            
            content = page.content()
            # movepageNew('1', '8', '2', '1', '1') 패턴 찾기
            # HTML 구조를 보기 위해 일부 출력
            print(f"HTML 길이: {len(content)}")
            
            # <tr> 태그를 기준으로 나누어서 각 행의 텍스트와 onclick 추출 시도
            rows = page.query_selector_all("tr")
            print(f"발견된 행 수: {len(rows)}")
            
            for i, row in enumerate(rows[:50]): # 상위 50개만 확인
                text = row.inner_text().strip().replace("\t", " ").replace("\n", " ")
                onclick = row.get_attribute("onclick")
                if onclick and "movepageNew" in onclick:
                    print(f"Row {i}: [{text}] -> {onclick}")
                    
        finally:
            browser.close()

if __name__ == "__main__":
    analyze_list()
