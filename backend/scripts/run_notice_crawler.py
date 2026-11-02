"""Run only the notice crawler in a Cloud Run Job."""

from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.crawlers.notice_crawler_v3 import crawl_notices_safely


if __name__ == "__main__":
    crawl_notices_safely(max_pages=5)
