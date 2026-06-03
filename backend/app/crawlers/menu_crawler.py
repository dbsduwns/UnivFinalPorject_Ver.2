from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from app.database import SessionLocal
from app.models.daily_menu import DailyMenu
from app.core.ai_bot import campus_ai_bot
from app.core.notification import notify_users_by_type_sync
from langchain_core.documents import Document
from dotenv import load_dotenv
from pathlib import Path
import os, json, requests, re, datetime, time

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

def login(page):
    load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)
    knu_user_id = os.getenv("KNU_USER_ID")
    knu_password = os.getenv("KNU_PASSWORD")

    if not knu_user_id or not knu_password:
        raise RuntimeError("KNU_USER_ID and KNU_PASSWORD must be set in .env")

    page.goto("https://nsso.kangnam.ac.kr/sso/auth?response_type=code&client_id=HOMEPAGE&redirect_uri=https://web.kangnam.ac.kr/nsso/login_proc.jsp")
    page.wait_for_load_state("networkidle")

    page.fill("input[name='user_id']", knu_user_id)
    page.fill("input[name='pw']", knu_password)

    page.click("button[type='submit']")
    page.wait_for_load_state("networkidle")
    if page.locator("input[name='user_id']").count() > 0:
        raise RuntimeError("KNU login failed")

    if "kangnam.ac.kr" in page.url:
        print("로그인 성공!")
    else:
        print("로그인 실패!")

def detail_img_url(page, detail_url):
    page.goto(detail_url, timeout=60000)
    page.wait_for_load_state("networkidle")

    html = page.content()
    soup = BeautifulSoup(html, "html.parser")

    content = soup.select_one("div.tbl_view")
    if content:
        img = content.select_one("img")
        if img:
            return f"https://web.kangnam.ac.kr{img.get('src')}"
    return None

def download_img(image_url, filename):
    response = requests.get(image_url)

    with open(filename, "wb") as f:
        f.write(response.content)

        print(f"이미지 저장 완료: {filename}")

def crawl_menu_list(max_items: int | None = None):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        login(page)

        page.goto("https://web.kangnam.ac.kr/menu/ddc681caea557950be41fc172d7b8142.do")
        page.wait_for_load_state("networkidle")
        try:
            page.wait_for_selector("a.detailLink", timeout=15000)
        except Exception:
            pass

        links = page.query_selector_all("a.detailLink")

        menus = []

        for link in links:
            if max_items is not None and len(menus) >= max_items:
                break

            try:
                title = link.inner_text().strip()
                data_params = json.loads(link.get_attribute("data-params"))
                enc_menu_seq = data_params["encMenuSeq"]
                enc_menu_board_seq = data_params["encMenuBoardSeq"]
                detail_url = f"https://web.kangnam.ac.kr/menu/board/info/ddc681caea557950be41fc172d7b8142.do?scrtWrtiYn=false&encMenuSeq={enc_menu_seq}&encMenuBoardSeq={enc_menu_board_seq}"
                
                print(f"  ▶ 상세 수집 중: {title}")

                # 별도의 탭을 열지 않고 현재 탭이나 새 탭을 조심스럽게 관리
                detail_page = browser.new_page()
                try:
                    image_url = detail_img_url(detail_page, detail_url)
                except Exception as e:
                    print(f"    ⚠️ 상세 이미지 추출 실패: {e}")
                    image_url = None
                finally:
                    detail_page.close()

                menus.append({
                    "title": title,
                    "image_url": image_url
                })
                
                # 서버 부하 방지 및 안정성 확보를 위한 짧은 대기
                time.sleep(1)
            except Exception as e:
                print(f"  ⚠️ 공지 항목 처리 중 에러 발생 (건너뜀): {e}")
                continue
        browser.close()
        return menus

def extract_dates(title):
    match = re.search(r'(\d{4})\.(\d{2})\.(\d{2})\s*~\s*([\d\.]+)', title)
    if not match:
        return []

    year = int(match.group(1))
    month = int(match.group(2))
    day = int(match.group(3))
    start_date = datetime.date(year, month, day)

    end_val = match.group(4)
    parts = list(map(int, end_val.split('.')))
    
    if len(parts) == 1:
        end_day = parts[0]
        try:
            end_date = datetime.date(year, month, end_day)
            if end_date < start_date:
                raise ValueError
        except ValueError:
            if month == 12:
                end_date = datetime.date(year + 1, 1, end_day)
            else:
                end_date = datetime.date(year, month + 1, end_day)

    elif len(parts) == 2:
        end_month, end_day = parts
        end_date = datetime.date(year, end_month, end_day)
        if end_date < start_date:
            end_date = datetime.date(year + 1, end_month, end_day)

    elif len(parts) == 3:
        end_year, end_month, end_day = parts
        end_date = datetime.date(end_year, end_month, end_day)
    else:
        return []

    dates = []
    curr = start_date
    while curr <= end_date:
        dates.append(curr)
        curr += datetime.timedelta(days=1)
    
    if len(dates) > 10:
        return []
        
    return dates

def save_menus(menus: list):
    db = SessionLocal()
    indexed_docs = []
    try:
        for m in menus:
            dates = extract_dates(m["title"])

            for menu_date in dates:
                # 1. DB 저장 (중복 체크 강화)
                existing = db.query(DailyMenu).filter(
                    DailyMenu.menu_date == menu_date
                ).first()
                if existing:
                    continue
                
                menu = DailyMenu(
                    menu_date=menu_date,
                    image_url=m["image_url"]
                )
                db.add(menu)
                
                # 2. RAG 인덱싱: AI가 이 정보를 알고 '학식 탭'으로 유도하게 함
                doc = Document(
                    page_content=f"{menu_date}의 학식 메뉴(식단표)가 등록되어 있습니다. 상세한 이미지는 앱의 '오늘의 학식' 탭에서 확인하실 수 있습니다.",
                    metadata={
                        "source": "학식",
                        "date": str(menu_date),
                        "action": "move_to_meal_tab" # 프론트엔드 연동용 마커
                    }
                )
                indexed_docs.append(doc)
        
        db.commit()
        
        # 벡터 DB에 추가
        if indexed_docs:
            campus_ai_bot.add_documents(indexed_docs)
            
            # 푸시 알림 전송 (새로운 식단이 추가된 경우에만)
            notify_users_by_type_sync(
                db, 
                "cafeteria_alert", 
                "🍱 새로운 식단표 업데이트", 
                "이번 주 새로운 식단표가 등록되었습니다. 지금 확인해보세요!"
            )
            
        print(f"✅ {len(indexed_docs)}일치 학식 데이터 저장 및 인덱싱 완료")
    except Exception as e:
        print(f"❌ 학식 저장 중 오류 발생: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    menus = crawl_menu_list()
    save_menus(menus)
