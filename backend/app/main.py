from fastapi import FastAPI
from sqlalchemy import text
from app.database import Base, SessionLocal, engin
from app.models import (
    building,
    chat_room,
    course,
    course_schedule,
    custom_schedule,
    message,
    subject,
    timetable,
    timetable_course,
    user,
)
from app.routers import auth, notice, daily_menu, timetable, chat, course
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
app.include_router(timetable.router)
app.include_router(chat.router)
app.include_router(course.router)


@app.on_event("startup")
def create_missing_tables():
    Base.metadata.create_all(bind=engin)

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

@app.get("/health")
def root():
    return {"message": "KNU CAMPUS API server is running"}

@app.get("/health/db")
def database_health_check():
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    finally:
        db.close()
