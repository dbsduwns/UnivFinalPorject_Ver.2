from fastapi import FastAPI
from app.routers import auth, notice, daily_menu
from apscheduler.schedulers.background import BackgroundScheduler
from app.crawlers.notice_crawler import crawl_notice_list, save_notices
from app.crawlers.menu_crawler import crawl_menu_list, save_menus

app = FastAPI(
    title="KNU CAMPUS API",
    description="강남대학교 통합 앱 API",
    version="1.0.0",
)

app.include_router(auth.router)
app.include_router(notice.router)
app.include_router(daily_menu.router)

def run_notice_crawler():
    print("🕷️ 공지사항 크롤링 시작...")
    notices = crawl_notice_list()
    save_notices(notices)
    print("✅ 크롤링 완료!")

def run_menu_crawler():
    print("🥣 학식 메뉴 크롤링 시작...")
    daily_menus = crawl_menu_list()
    save_menus(daily_menus)
    print("✅ 크롤링 완료!")

scheduler = BackgroundScheduler()
scheduler.add_job(run_notice_crawler, "interval", hours=1)
scheduler.add_job(run_menu_crawler, "interval", hours=24)
scheduler.start()

@app.get("/")
def root():
    return {"message": "KNU CMPUS API 서버 정상 작동 중"}