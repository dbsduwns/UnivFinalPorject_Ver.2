"""RAG 메타데이터 필터용 Qdrant payload index를 생성합니다.

이 스크립트는 기존 인덱스와 타입을 먼저 확인합니다. 같은 타입의 인덱스는
건너뛰고, 다른 타입이 이미 있으면 자동으로 삭제하거나 덮어쓰지 않습니다.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

load_dotenv(BACKEND_DIR / ".env")
load_dotenv(BACKEND_DIR / ".env.cloudrun", override=True)

from qdrant_client import QdrantClient  # noqa: E402
from qdrant_client.models import PayloadSchemaType  # noqa: E402


INDEX_SPECS = {
    "metadata.source": PayloadSchemaType.KEYWORD,
    "metadata.category": PayloadSchemaType.KEYWORD,
    "metadata.academic_year": PayloadSchemaType.INTEGER,
    "metadata.date": PayloadSchemaType.KEYWORD,
}


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} 환경변수가 필요합니다.")
    return value


def ensure_payload_indexes(
    client: QdrantClient,
    collection_name: str,
    *,
    dry_run: bool = False,
) -> dict[str, list[str]]:
    if not client.collection_exists(collection_name):
        raise RuntimeError(f"Qdrant 컬렉션이 없습니다: {collection_name}")

    collection = client.get_collection(collection_name)
    payload_schema = collection.payload_schema or {}
    created: list[str] = []
    skipped: list[str] = []
    planned: list[str] = []

    for field_name, expected_type in INDEX_SPECS.items():
        existing = payload_schema.get(field_name)
        if existing is not None:
            if existing.data_type != expected_type:
                raise RuntimeError(
                    f"{field_name} 인덱스 타입이 다릅니다: "
                    f"현재={existing.data_type.value}, 필요={expected_type.value}"
                )
            print(f"[SKIP] {field_name}: {expected_type.value} 인덱스가 이미 있습니다.")
            skipped.append(field_name)
            continue

        if dry_run:
            print(f"[PLAN] {field_name}: {expected_type.value} 인덱스를 생성합니다.")
            planned.append(field_name)
            continue

        client.create_payload_index(
            collection_name=collection_name,
            field_name=field_name,
            field_schema=expected_type,
            wait=True,
        )
        print(f"[OK] {field_name}: {expected_type.value} 인덱스 생성 완료")
        created.append(field_name)

    if not dry_run:
        verified_schema = client.get_collection(collection_name).payload_schema or {}
        for field_name, expected_type in INDEX_SPECS.items():
            actual = verified_schema.get(field_name)
            if actual is None or actual.data_type != expected_type:
                raise RuntimeError(f"payload index 생성 확인 실패: {field_name}")

    return {
        "created": created,
        "skipped": skipped,
        "planned": planned,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Qdrant RAG 메타데이터 필터용 payload index를 생성합니다."
    )
    parser.add_argument(
        "--collection",
        default=os.getenv("QDRANT_COLLECTION", "knu-campus-bge-m3"),
        help="대상 Qdrant 컬렉션 이름",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="현재 상태와 생성 예정 항목만 확인하고 변경하지 않음",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    client = QdrantClient(
        url=require_env("QDRANT_URL"),
        api_key=require_env("QDRANT_API_KEY"),
        prefer_grpc=False,
        timeout=30,
        check_compatibility=False,
    )
    print(f"Qdrant collection: {args.collection}")
    result = ensure_payload_indexes(
        client,
        args.collection,
        dry_run=args.dry_run,
    )
    print(
        "완료: "
        f"생성 {len(result['created'])}개, "
        f"기존 {len(result['skipped'])}개, "
        f"생성 예정 {len(result['planned'])}개"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
