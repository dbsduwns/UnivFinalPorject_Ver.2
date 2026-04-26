from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from app.database import SessionLocal
from app.models.daily_menu import DailyMenu
from app.models.menu_item import MenuItem
from dotenv import load_dotenv
import os, json, requests, re, datetime
load_dotenv()

KNU_USER_ID = os.getenv("KNU_USER_ID")
KNU_PASSWORD = os.getenv("KNU_PASSWORD")

def login(page):
    page.goto("https://nsso.kangnam.ac.kr/sso/auth?response_type=code&client_id=HOMEPAGE&redirect_uri=https://web.kangnam.ac.kr/nsso/login_proc.jsp")
    page.wait_for_load_state("networkidle")

    page.fill("input[name='user_id']", KNU_USER_ID)
    page.fill("input[name='pw']", KNU_PASSWORD)

    page.click("button[type='submit']")
    page.wait_for_load_state("networkidle")

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

def crawl_menu_list():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        login(page)

        page.goto("https://web.kangnam.ac.kr/menu/ddc681caea557950be41fc172d7b8142.do")
        page.wait_for_load_state("networkidle")

        links = page.query_selector_all("a.detailLink")

        menus = []

        for link in links:
            title = link.inner_text().strip()
            data_params = json.loads(link.get_attribute("data-params"))
            enc_menu_seq = data_params["encMenuSeq"]
            enc_menu_board_seq = data_params["encMenuBoardSeq"]
            detail_url = f"https://web.kangnam.ac.kr/menu/board/info/ddc681caea557950be41fc172d7b8142.do?scrtWrtiYn=false&encMenuSeq={enc_menu_seq}&encMenuBoardSeq={enc_menu_board_seq}"
            
            print(f"제목: {title}")
            print(f"encMenuSeq: {enc_menu_seq}")
            print(f"encMenuBoardSeq: {enc_menu_board_seq}")
            print(f"상세 URL: {detail_url}")

            detail_page = browser.new_page()
            image_url = detail_img_url(detail_page, detail_url)
            detail_page.close()

            menus.append({
                "title": title,
                "image_url": image_url
            })
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
    try:
        for m in menus:
            dates = extract_dates(m["title"])

            for menu_date in dates:
                existing = db.query(DailyMenu).filter(
                    DailyMenu.menu_date == menu_date,
                    DailyMenu.image_url == m["image_url"]
                ).first()
                if existing:
                    continue
                menu = DailyMenu(
                    menu_date=menu_date,
                    image_url=m["image_url"]
                )
                db.add(menu)
        db.commit()
        print("저장완료")
    finally:
        db.close()

if __name__ == "__main__":
    menus = crawl_menu_list()
    save_menus(menus)