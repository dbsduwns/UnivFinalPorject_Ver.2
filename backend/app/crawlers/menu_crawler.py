from app.core.university_http import university_get
from playwright.sync_api import Error as PlaywrightError, sync_playwright
from bs4 import BeautifulSoup
from app.database import SessionLocal
from app.models.daily_menu import DailyMenu
from app.models.menu_item import MenuItem
from app.core.ai_bot import campus_ai_bot
from app.core.notification import notify_users_by_type_sync
from app.services.menu_ocr import extract_weekly_menu
from langchain_core.documents import Document
from dotenv import load_dotenv
from pathlib import Path
from urllib.parse import urljoin
import os, json, requests, re, datetime, time, hashlib

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def _looks_like_image(content: bytes) -> bool:
    return content.startswith((b"\xff\xd8\xff", b"\x89PNG", b"GIF8", b"BM")) or (
        content.startswith(b"RIFF") and content[8:12] == b"WEBP"
    )

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

def detail_image(page, detail_url):
    page.goto(detail_url, timeout=60000)
    page.wait_for_load_state("networkidle")

    html = page.content()
    soup = BeautifulSoup(html, "html.parser")

    content = soup.select_one("div.tbl_view")
    if content:
        img = content.select_one("img")
        if img:
            image_url = urljoin(detail_url, img.get("src"))
            # Reuse the authenticated Playwright context. This avoids both lost
            # portal cookies and CA-chain differences between Chromium and requests.
            try:
                response = page.request.get(image_url, timeout=60000)
                if response.ok:
                    response_body = response.body()
                    if _looks_like_image(response_body):
                        return image_url, response_body
                    request_error = RuntimeError(
                        "이미지 요청이 이미지가 아닌 응답을 반환했습니다."
                    )
                else:
                    request_error = RuntimeError(
                        f"식단 이미지 다운로드 실패: HTTP {response.status}"
                    )
            except Exception as exc:
                request_error = exc

            # Some menu images use Content-Disposition: attachment. In that case
            # page.goto() intentionally raises "Download is starting", while the
            # download event still contains the complete image file.
            try:
                with page.expect_download(timeout=60000) as download_info:
                    try:
                        page.goto(image_url, wait_until="commit", timeout=60000)
                    except PlaywrightError as exc:
                        if "Download is starting" not in str(exc):
                            raise
                download = download_info.value
                download_path = download.path()
                if not download_path:
                    raise RuntimeError("다운로드된 식단 이미지 경로를 찾지 못했습니다.")
                downloaded_bytes = Path(download_path).read_bytes()
                if not _looks_like_image(downloaded_bytes):
                    raise RuntimeError("다운로드 결과가 이미지 형식이 아닙니다.")
                return image_url, downloaded_bytes
            except Exception as download_exc:
                raise RuntimeError(
                    "로그인된 브라우저에서도 식단 이미지를 받지 못했습니다: "
                    f"request={request_error}; download={download_exc}"
                ) from download_exc
    return None, None


def detail_img_url(page, detail_url):
    """Backward-compatible helper for callers that only need the image URL."""
    image_url, _ = detail_image(page, detail_url)
    return image_url

def download_img(image_url, filename):
    response = university_get(image_url, timeout=30)
    response.raise_for_status()

    with open(filename, "wb") as f:
        f.write(response.content)

        print(f"이미지 저장 완료: {filename}")


def download_image_bytes(image_url: str) -> bytes:
    response = university_get(image_url, timeout=30)
    response.raise_for_status()
    return response.content

def crawl_menu_list(max_items: int | None = None):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

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
                detail_page = context.new_page()
                try:
                    image_url, image_bytes = detail_image(detail_page, detail_url)
                except Exception as e:
                    print(f"    ⚠️ 상세 이미지 추출 실패: {e}")
                    image_url = None
                    image_bytes = None
                finally:
                    detail_page.close()

                menus.append({
                    "title": title,
                    "image_url": image_url,
                    # Internal value consumed and removed by save_menus().
                    "_image_bytes": image_bytes,
                })
                
                # 서버 부하 방지 및 안정성 확보를 위한 짧은 대기
                time.sleep(1)
            except Exception as e:
                print(f"  ⚠️ 공지 항목 처리 중 에러 발생 (건너뜀): {e}")
                continue
        context.close()
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
    changed_dates = 0
    try:
        for m in menus:
            dates = extract_dates(m["title"])
            if not dates:
                print(f"⚠️ 식단 날짜를 찾지 못해 건너뜁니다: {m['title']}")
                continue

            image_url = m.get("image_url")
            crawled_image_bytes = m.pop("_image_bytes", None)
            image_sha256 = None
            extracted_by_date = None
            ocr_error = None
            try:
                if not image_url:
                    raise ValueError("식단 이미지 URL이 없습니다.")
                image_bytes = crawled_image_bytes or download_image_bytes(image_url)
                image_sha256 = hashlib.sha256(image_bytes).hexdigest()

                existing_dates = (
                    db.query(DailyMenu)
                    .filter(DailyMenu.menu_date.in_(dates))
                    .all()
                )
                already_processed = (
                    len(existing_dates) == len(dates)
                    and all(
                        row.image_sha256 == image_sha256
                        and row.ocr_status == "completed"
                        and bool(row.menu_items)
                        for row in existing_dates
                    )
                )
                if already_processed:
                    print(f"ℹ️ 동일한 식단 이미지는 OCR을 생략합니다: {m['title']}")
                    continue

                extracted_by_date = extract_weekly_menu(image_bytes, dates)
            except Exception as exc:
                ocr_error = str(exc)[:2000]
                print(f"⚠️ 식단 OCR 실패 ({m['title']}): {ocr_error}")

            for menu_date in dates:
                menu = db.query(DailyMenu).filter(
                    DailyMenu.menu_date == menu_date
                ).first()
                is_new = menu is None
                if menu is None:
                    menu = DailyMenu(menu_date=menu_date)
                    db.add(menu)
                    db.flush()

                menu.image_url = image_url
                if image_sha256:
                    menu.image_sha256 = image_sha256
                sections = (extracted_by_date or {}).get(menu_date, [])
                if extracted_by_date is not None:
                    db.query(MenuItem).filter(
                        MenuItem.daily_menu_id == menu.id
                    ).delete(synchronize_session=False)
                    for section in sections:
                        for item_name in section.items:
                            db.add(
                                MenuItem(
                                    daily_menu_id=menu.id,
                                    name=item_name,
                                    meal_type=section.meal_type,
                                    corner=section.corner,
                                    price=section.price,
                                )
                            )
                    menu.ocr_status = "completed"
                    menu.ocr_error = None
                else:
                    menu.ocr_status = "failed"
                    menu.ocr_error = ocr_error

                menu_lines = [
                    f"{section.meal_type} {section.corner}: {', '.join(section.items)}"
                    for section in sections
                    if section.items
                ]
                if menu_lines:
                    page_content = (
                        f"{menu_date} 강남대학교 학생식당 메뉴입니다.\n"
                        + "\n".join(menu_lines)
                    )
                else:
                    page_content = (
                        f"{menu_date}의 학식 메뉴(식단표)가 등록되어 있습니다. "
                        "상세한 이미지는 앱의 '오늘의 학식' 탭에서 확인하실 수 있습니다."
                    )

                if extracted_by_date is not None or is_new:
                    doc = Document(
                        page_content=page_content,
                        metadata={
                            "source": "학식",
                            "date": str(menu_date),
                            "title": f"{menu_date} 학생식당 메뉴",
                            "ocr_status": menu.ocr_status,
                            "action": "move_to_meal_tab",
                        }
                    )
                    indexed_docs.append(doc)
                    changed_dates += 1
        
        db.commit()
        
        if indexed_docs:
            try:
                campus_ai_bot.add_documents(indexed_docs)
            except Exception as exc:
                print(f"⚠️ 학식 DB 저장은 완료됐지만 RAG 인덱싱에 실패했습니다: {exc}")

            try:
                notify_users_by_type_sync(
                    db,
                    "cafeteria_alert",
                    "🍱 새로운 식단표 업데이트",
                    "이번 주 새로운 식단표가 등록되었습니다. 지금 확인해보세요!"
                )
            except Exception as exc:
                print(f"⚠️ 학식 알림 전송 실패: {exc}")

        print(f"✅ {changed_dates}일치 학식 데이터 저장 완료")
    except Exception as e:
        print(f"❌ 학식 저장 중 오류 발생: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    menus = crawl_menu_list()
    save_menus(menus)
