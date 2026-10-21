"""공지사항·식단·셔틀 크롤러를 순서대로 실행합니다.

Cloud Run Job에서 ``python scripts/run_daily_crawlers.py``로 실행해도
프로젝트 루트의 ``app`` 패키지를 찾을 수 있도록 실행 경로를 보정합니다.
"""

from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.crawlers import menu_crawler, notice_crawler_v3, shuttle_crawler


def main():
    notice_crawler_v3.crawl_notices_safely(max_pages=5)

    menus = menu_crawler.crawl_menu_list()
    menu_crawler.save_menus(menus)

    schedule = shuttle_crawler.crawl_shuttle_schedule()
    shuttle_crawler.save_shuttle_schedule(schedule)


if __name__ == "__main__":
    main()
