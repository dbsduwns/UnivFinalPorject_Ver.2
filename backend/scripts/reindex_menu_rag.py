"""Rebuild Qdrant meal documents from OCR results stored in PostgreSQL."""

from __future__ import annotations

import argparse
from datetime import date
import os
from pathlib import Path
import sys

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env", override=True)

from langchain_core.documents import Document  # noqa: E402
from sqlalchemy.orm import selectinload  # noqa: E402

from app.core.ai_bot import campus_ai_bot  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models.daily_menu import DailyMenu  # noqa: E402
from app.services.menu_ocr import remove_parenthetical_content  # noqa: E402


def parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("날짜는 YYYY-MM-DD 형식이어야 합니다.") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PostgreSQL에 저장된 OCR 식단을 Qdrant에 다시 인덱싱합니다."
    )
    parser.add_argument("--from-date", type=parse_date)
    parser.add_argument("--to-date", type=parse_date)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument(
        "--collection",
        default=os.getenv("QDRANT_COLLECTION", "knu-campus-bge-m3"),
        help="재인덱싱할 Qdrant 컬렉션 이름",
    )
    parser.add_argument(
        "--include-incomplete",
        action="store_true",
        help="OCR 완료 상태가 아니어도 메뉴 항목이 있으면 포함합니다.",
    )
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help="같은 날짜의 기존 학식 문서 중 새 문서가 아닌 포인트를 삭제합니다.",
    )
    parser.add_argument(
        "--cleanup-only",
        action="store_true",
        help="문서를 다시 임베딩하지 않고 기존 학식 문서 정리만 수행합니다.",
    )
    return parser.parse_args()


def build_document(menu: DailyMenu) -> Document | None:
    grouped: dict[tuple[str, str, int | None], list[str]] = {}
    for item in menu.menu_items:
        item_name = remove_parenthetical_content(item.name)
        if not item_name:
            continue
        key = (item.meal_type or "식사", item.corner or "메뉴", item.price)
        grouped.setdefault(key, []).append(item_name)

    if not grouped:
        return None

    lines = []
    for (meal_type, corner, price), item_names in grouped.items():
        price_text = f" · {price:,}원" if price is not None else ""
        lines.append(
            f"{meal_type} {corner}{price_text}: {', '.join(item_names)}"
        )

    return Document(
        page_content=(
            f"{menu.menu_date} 강남대학교 학생식당 메뉴입니다.\n"
            + "\n".join(lines)
        ),
        metadata={
            "source": "학식",
            "date": str(menu.menu_date),
            "title": f"{menu.menu_date} 학생식당 메뉴",
            "ocr_status": menu.ocr_status,
            "action": "move_to_meal_tab",
        },
    )


def remove_stale_documents(vectorstore, documents: list[Document]) -> int:
    from qdrant_client.models import PointIdsList

    expected_by_date = {
        str(document.metadata["date"]): vectorstore._point_id(
            vectorstore._document_id(document)
        )
        for document in documents
    }
    stale_ids = []
    offset = None
    while True:
        records, offset = vectorstore.client.scroll(
            collection_name=vectorstore.collection_name,
            offset=offset,
            limit=256,
            with_payload=True,
            with_vectors=False,
        )
        for record in records:
            payload = record.payload or {}
            metadata = payload.get("metadata") or {}
            if metadata.get("source") != "학식":
                continue
            menu_date = str(metadata.get("date") or "")
            expected_id = expected_by_date.get(menu_date)
            if expected_id and str(record.id) != expected_id:
                stale_ids.append(record.id)
        if offset is None:
            break

    removed = 0
    for start in range(0, len(stale_ids), 256):
        batch = stale_ids[start : start + 256]
        vectorstore.client.delete(
            collection_name=vectorstore.collection_name,
            points_selector=PointIdsList(points=batch),
            wait=True,
        )
        removed += len(batch)
    return removed


def main() -> int:
    args = parse_args()
    if args.batch_size < 1:
        raise ValueError("--batch-size는 1 이상이어야 합니다.")
    if args.from_date and args.to_date and args.from_date > args.to_date:
        raise ValueError("--from-date는 --to-date보다 늦을 수 없습니다.")

    # CampusAIBot reads the collection name when initialize() is called below.
    os.environ["QDRANT_COLLECTION"] = args.collection

    with SessionLocal() as db:
        query = db.query(DailyMenu).options(selectinload(DailyMenu.menu_items))
        if not args.include_incomplete:
            query = query.filter(DailyMenu.ocr_status == "completed")
        if args.from_date:
            query = query.filter(DailyMenu.menu_date >= args.from_date)
        if args.to_date:
            query = query.filter(DailyMenu.menu_date <= args.to_date)
        menus = query.order_by(DailyMenu.menu_date).all()
        documents = [document for menu in menus if (document := build_document(menu))]

    if not documents:
        print("재인덱싱할 OCR 식단 문서가 없습니다.")
        return 0

    if not campus_ai_bot.initialize() or not campus_ai_bot.vectorstore:
        raise RuntimeError(
            "Qdrant가 준비되지 않았습니다. QDRANT_URL과 QDRANT_API_KEY를 확인하세요."
        )

    total = len(documents)
    if not args.cleanup_only:
        for start in range(0, total, args.batch_size):
            batch = documents[start : start + args.batch_size]
            campus_ai_bot.add_documents(batch)
            print(f"Qdrant 재인덱싱: {min(start + len(batch), total)}/{total}")

    if args.replace_existing or args.cleanup_only:
        removed = remove_stale_documents(campus_ai_bot.vectorstore, documents)
        print(f"기존 학식 문서 정리: {removed}개 삭제")

    if args.cleanup_only:
        print(f"학식 문서 정리 완료: {args.collection}")
    else:
        print(f"학식 문서 {total}개 재인덱싱 완료: {args.collection}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
