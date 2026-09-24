from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.database import Base, SessionLocal, engine
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
    daily_menu,
    menu_item,
    notice,
    shuttle,
    friendship,
)
from app.routers import auth, notice as notice_router, daily_menu as daily_menu_router, timetable as timetable_router, chat, course as course_router
from app.routers import shuttle as shuttle_router, friend as friend_router
from app.core.ai_bot import campus_ai_bot
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import os

# 새롭게 개선된 크롤러들 임포트
from app.crawlers.rules_crawler import crawl_rules
from fastapi.staticfiles import StaticFiles

STATIC_DIR = "static"
SHUTTLE_DIR = os.path.join(STATIC_DIR, "shuttle")
os.makedirs(SHUTTLE_DIR, exist_ok=True)

app = FastAPI(
    title="KNU CAMPUS API",
    description="강남대학교 통합 앱 API",
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(notice_router.router)
app.include_router(daily_menu_router.router)
app.include_router(timetable_router.router)
app.include_router(chat.router)
app.include_router(course_router.router)
app.include_router(shuttle_router.router)
app.include_router(friend_router.router)


@app.on_event("startup")
def startup_event():
    # 1. DB 테이블 생성
    Base.metadata.create_all(bind=engine)

    # 2. 서버 시작 시 즉시 크롤링 예약 (순차적으로 실행하여 자원 충돌 방지)
    print("🚀 [Startup] 서버 시작 - 초기 데이터 동기화 예약 중...")
    from datetime import timedelta
    
    # 1. 학식 메뉴: 즉시 시작
    scheduler.add_job(run_menu_crawler, 'date', run_date=datetime.now())
    # 2. 셔틀 시간표: 1분 후 시작
    scheduler.add_job(run_shuttle_crawler, 'date', run_date=datetime.now() + timedelta(minutes=1))
    # 3. 공지사항: 2분 후 시작
    scheduler.add_job(run_notice_crawler, 'date', run_date=datetime.now() + timedelta(minutes=2))

def run_notice_crawler():
    from app.crawlers.notice_crawler_v3 import crawl_notices_safely
    print("🕷️ [Scheduler] 공지사항 크롤링 시작 (V3)...")
    try:
        # 최근 5페이지 정도만 주기적으로 확인 (서버 부하 방지)
        crawl_notices_safely(max_pages=5)
        print("✅ [Scheduler] 공지사항 크롤링 완료!")
    except Exception as e:
        print(f"❌ [Scheduler] 공지사항 크롤링 중 오류: {e}")

def run_menu_crawler():
    from app.crawlers.menu_crawler import crawl_menu_list, save_menus
    print("🥣 [Scheduler] 학식 메뉴 크롤링 시작...")
    try:
        daily_menus = crawl_menu_list()
        save_menus(daily_menus)
        print("✅ [Scheduler] 학식 메뉴 크롤링 완료!")
    except Exception as e:
        print(f"❌ [Scheduler] 학식 메뉴 크롤링 중 오류: {e}")

def run_shuttle_crawler():
    from app.crawlers.shuttle_crawler import crawl_shuttle_schedule, save_shuttle_schedule
    print("🚌 [Scheduler] 셔틀 시간표 크롤링 시작...")
    try:
        schedule = crawl_shuttle_schedule()
        save_shuttle_schedule(schedule)
        print("✅ [Scheduler] 셔틀 시간표 크롤링 완료!")
    except Exception as e:
        print(f"❌ [Scheduler] 셔틀 시간표 크롤링 중 오류: {e}")

# 스케줄러 설정
# scheduler = BackgroundScheduler()
# 공지사항: 1시간마다 최신 데이터 확인
# scheduler.add_job(run_notice_crawler, "interval", hours=1)
# 학식: 매일 새벽 1시에 수집
# scheduler.add_job(run_menu_crawler, "cron", hour=1, minute=0)
# 셔틀: 12시간마다 확인
# scheduler.add_job(run_shuttle_crawler, "interval", hours=12)
# scheduler.start()

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
