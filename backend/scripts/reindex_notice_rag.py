"""Rebuild all notice documents in the configured Qdrant collection."""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")
load_dotenv(BACKEND_DIR / ".env.cloudrun", override=True)

from app.core.ai_bot import campus_ai_bot  # noqa: E402
from scripts.init_rag_db import index_notices  # noqa: E402


def main() -> None:
    print("⏳ 공지사항 전체 RAG 재색인을 시작합니다.", flush=True)
    campus_ai_bot.initialize()
    if not campus_ai_bot.indexing_ready:
        raise RuntimeError("Qdrant가 준비되지 않아 재색인을 진행할 수 없습니다.")

    count = index_notices()
    print(f"✅ 공지사항 RAG 재색인 완료: {count}개 청크", flush=True)


if __name__ == "__main__":
    main()
