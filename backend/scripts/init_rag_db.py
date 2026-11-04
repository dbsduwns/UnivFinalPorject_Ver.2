import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

# 평가·마이그레이션 스크립트와 같은 Qdrant 설정을 사용합니다.
load_dotenv(BACKEND_DIR / ".env")
load_dotenv(BACKEND_DIR / ".env.cloudrun", override=True)

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.notice import Notice
from app.core.ai_bot import campus_ai_bot
from langchain_core.documents import Document
from scripts.seed_shuttle_map import (
    DEFAULT_SEED_PATH,
    build_shuttle_rag_records,
    load_seed_data,
    seed_shuttle_map,
)


NOTICE_CHUNK_CHARACTERS = 6_000
NOTICE_CHUNK_OVERLAP = 500


def build_notice_records(notices: list[Notice]) -> list[tuple[str, Document]]:
    records: list[tuple[str, Document]] = []
    step = NOTICE_CHUNK_CHARACTERS - NOTICE_CHUNK_OVERLAP
    for notice in notices:
        content = (notice.content or "").strip()
        if not content:
            continue

        chunks = [
            content[start : start + NOTICE_CHUNK_CHARACTERS]
            for start in range(0, len(content), step)
        ]
        for chunk_index, chunk in enumerate(chunks):
            source_id = f"notice:{notice.id}:chunk:{chunk_index}"
            records.append(
                (
                    source_id,
                    Document(
                        page_content=(
                            f"제목: {notice.title}\n"
                            f"카테고리: {notice.category}\n"
                            f"내용: {chunk}"
                        ),
                        metadata={
                            "source": "공지사항",
                            "source_key": notice.source_key,
                            "notice_id": notice.id,
                            "source_document_id": f"notice:{notice.id}",
                            "chunk_index": chunk_index,
                            "chunk_count": len(chunks),
                            "category": notice.category,
                            "title": notice.title,
                            "source_url": notice.source_url,
                            "published_at": (
                                notice.published_at.isoformat()
                                if notice.published_at
                                else None
                            ),
                        },
                    ),
                )
            )
    return records


def index_notices() -> int:
    db: Session = SessionLocal()
    try:
        notices = db.query(Notice).all()
        print(f"📦 총 {len(notices)}개의 공지사항을 처리 중...")
        records = build_notice_records(notices)
    finally:
        db.close()

    if not records:
        print("ℹ️ 인덱싱할 공지사항이 없습니다.")
        return 0

    ids = [source_id for source_id, _ in records]
    documents = [document for _, document in records]
    vectorstore = campus_ai_bot.vectorstore
    if hasattr(vectorstore, "replace_documents_by_source"):
        removed = vectorstore.replace_documents_by_source(
            documents,
            ids=ids,
            source="공지사항",
        )
        print(
            f"✅ 공지사항 {len(documents)}개 청크 인덱싱 완료 "
            f"(이전 문서 {removed}개 정리)!"
        )
    else:
        campus_ai_bot.add_documents(documents)
        print(f"✅ 공지사항 {len(documents)}개 청크 인덱싱 완료!")
    return len(documents)


def index_shuttle_seed(seed_path: Path) -> int:
    payload = load_seed_data(seed_path)
    records = build_shuttle_rag_records(payload)
    ids = [source_id for source_id, _ in records]
    documents = [document for _, document in records]

    vectorstore = campus_ai_bot.vectorstore
    if hasattr(vectorstore, "replace_documents_by_source"):
        removed = vectorstore.replace_documents_by_source(
            documents,
            ids=ids,
            source="셔틀시간표",
        )
        print(
            f"✅ 셔틀 시간표 {len(documents)}개 인덱싱 완료 "
            f"(이전 문서 {removed}개 정리)!"
        )
    else:
        campus_ai_bot.add_documents(documents)
        print(f"✅ 셔틀 시간표 {len(documents)}개 인덱싱 완료!")
    return len(documents)


def init_db(
    seed_path: Path = DEFAULT_SEED_PATH,
    *,
    seed_relational_db: bool = True,
    include_notices: bool = True,
):
    print("⏳ 기존 데이터를 벡터 DB에 인덱싱 시작...")

    # Qdrant에 쓰기 전에 전체 셔틀 시드 구조를 먼저 검증합니다.
    load_seed_data(seed_path)

    if seed_relational_db:
        print("🚌 셔틀 운행 데이터를 관계형 DB에 반영 중...")
        seed_shuttle_map(seed_path)

    # AI 봇 초기화
    campus_ai_bot.initialize()
    if not campus_ai_bot.indexing_ready:
        raise RuntimeError("Qdrant가 준비되지 않아 RAG 초기화를 진행할 수 없습니다.")

    # 1. 공지사항 인덱싱
    if include_notices:
        index_notices()
    else:
        print("⏭️ 기존 공지사항 인덱싱을 건너뜁니다.")

    # 2. 셔틀 운행 시드를 노선·요일별 문서로 Qdrant에 동기화
    index_shuttle_seed(seed_path)

    # 3. 기타 학사일정/학칙 등 추가 데이터가 있다면 여기에 작성
    # 예:
    # documents = [Document(page_content="졸업학점은 130학점입니다.", metadata={"source": "학칙"})]
    # campus_ai_bot.add_documents(documents)
    
    print("✨ 모든 인덱싱 작업이 완료되었습니다!")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="기존 관계형 DB 데이터와 셔틀 시드를 Qdrant에 인덱싱합니다."
    )
    parser.add_argument(
        "--seed-path",
        type=Path,
        default=DEFAULT_SEED_PATH,
        help="셔틀맵 seed JSON 경로",
    )
    parser.add_argument(
        "--skip-shuttle-db",
        action="store_true",
        help="셔틀 관계형 DB 적재는 생략하고 Qdrant 인덱싱만 수행",
    )
    parser.add_argument(
        "--skip-notices",
        action="store_true",
        help="기존 공지사항은 유지하고 셔틀 문서만 Qdrant에 반영",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    init_db(
        args.seed_path,
        seed_relational_db=not args.skip_shuttle_db,
        include_notices=not args.skip_notices,
    )
