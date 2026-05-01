import os
import sys
import time
import re
from playwright.sync_api import sync_playwright
from langchain_core.documents import Document
from dotenv import load_dotenv
from pathlib import Path

# 현재 파일 기준으로 backend 폴더 경로 계산
backend_dir = str(Path(__file__).resolve().parents[2])
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from app.core.ai_bot import campus_ai_bot

# .env 로드
env_path = Path(backend_dir) / ".env"
load_dotenv(env_path)


# ── 크롤링 필터링 설정 ──────────────────────────────────────────────────
# 학생들에게 필요한 규정만 자동으로 골라내기 위한 조건입니다.
def should_crawl(name, pyon, jang):
    # 1. 제2편 1장 (학칙 등 가장 기본)
    if pyon == '2' and jang == '1': return True
    # 2. 제4편 전체 (교무행정 - 수강, 연구 등)
    if pyon == '4': return True
    # 3. 제5편 1, 2장 (학생행정, 장학금 등)
    if pyon == '5' and jang in ['1', '2']: return True
    # 4. 제6편 전체 (부속시설 - 기숙사, 도서관, 보건소 등)
    if pyon == '6': return True
    # 5. 제3편 5장 중 안전 및 개인정보 관련
    if pyon == '3' and jang == '5':
        if any(kw in name for kw in ["안전", "개인정보", "이동장치"]):
            return True
    return False

def get_auto_target_rules(page):
    """목록 페이지에서 전체 규정을 스캔하여 필터링된 대상 리스트를 반환한다."""
    print("🔍 전체 규정 목록 스캔 중...")
    targets = []
    
    # 목록 페이지 직접 접속
    page.goto(
        "https://app.kangnam.ac.kr/knumis/mo_open/rulesL1.jsp"
        "?rglt_cont2=&rglt_cont=&gubn=&save_gubn="
    )
    page.wait_for_load_state("networkidle")
    time.sleep(2)

    # 모든 행(tr)을 가져와서 분석
    rows = page.query_selector_all("tr")
    for row in rows:
        onclick = row.get_attribute("onclick")
        if onclick and "movepageNew" in onclick:
            # 패턴: movepageNew('true','행번호','편,장,번호')
            match = re.search(r"movepageNew\('.+?','(.+?)','(.+?),(.+?),(.+?)'\)", onclick)
            if match:
                row_no, pyon, jang, bnho = match.groups()
                # 텍스트에서 규정명만 추출 (탭이나 공백 제거)
                name = row.inner_text().strip().split('\t')[0].strip()
                
                if should_crawl(name, pyon, jang):
                    targets.append((name, row_no, pyon, jang, bnho))
    
    print(f"✅ 필터링 완료: 총 {len(targets)}개의 대상 규정을 찾았습니다.")
    return targets

def crawl_rules():
    all_docs = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page    = context.new_page()

        try:
            # ── 1. 로그인 ───────────────────────────────────────────────
            login(page)

            # ── 2. 대상 규정 자동 수집 ───────────────────────────────────
            target_rules = get_auto_target_rules(page)

            # ── 3. 규정별 순회하며 본문 수집 ─────────────────────────────
            for rule_name, row_no, pyon, jang, bnho in target_rules:
                full_text = load_rule_detail(
                    page, rule_name, row_no, pyon, jang, bnho
                )

                if not full_text:
                    continue

                docs = split_into_clauses(rule_name, full_text)
                print(f"  📄 '{rule_name}' → {len(docs)}개 조항 분할")
                all_docs.extend(docs)

                # 서버 부하 방지
                time.sleep(1)

        finally:
            browser.close()

    # ── 6. AI 인덱싱 ────────────────────────────────────────────────────
    if all_docs:
        print(f"\n🤖 총 {len(all_docs)}개 조항을 AI 챗봇에 인덱싱 중...")
        campus_ai_bot.add_documents(all_docs)
        print("✅ 인덱싱 완료!")
    else:
        print("\n❌ 수집된 문서가 없습니다.")


if __name__ == "__main__":
    crawl_rules()