from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")
load_dotenv(BACKEND_DIR / ".env.cloudrun", override=True)

import chromadb  # noqa: E402
from langchain_core.documents import Document  # noqa: E402

from app.core.ai_providers import build_embeddings  # noqa: E402
from app.core.vector_store import QdrantDocumentStore  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copy the local Chroma documents to the managed Qdrant collection."
    )
    parser.add_argument(
        "--chroma-path",
        default=str(BACKEND_DIR / "chroma_db"),
        help="Local Chroma persistence directory",
    )
    parser.add_argument(
        "--chroma-collection",
        default=os.getenv("CHROMA_COLLECTION", "langchain"),
    )
    parser.add_argument("--batch-size", type=int, default=5)
    parser.add_argument(
        "--start-index",
        type=int,
        default=0,
        help="Zero-based Chroma document index to resume from",
    )
    parser.add_argument(
        "--start-vector-index",
        type=int,
        default=0,
        help="Zero-based expanded vector index to resume from after document splitting",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=6000,
        help="Split unusually large documents into chunks of at most this size",
    )
    parser.add_argument("--chunk-overlap", type=int, default=500)
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=3.0,
        help="Minimum delay between embedding batches",
    )
    parser.add_argument(
        "--chars-per-minute",
        type=int,
        default=60000,
        help="Approximate character throughput used to pace embedding requests",
    )
    parser.add_argument("--max-retries", type=int, default=6)
    return parser.parse_args()


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} environment variable is required")
    return value


def split_document(
    source_id: str,
    document: Document,
    *,
    max_chars: int,
    overlap: int,
) -> list[tuple[str, Document]]:
    content = document.page_content
    if len(content) <= max_chars:
        return [(source_id, document)]

    step = max_chars - overlap
    if step <= 0:
        raise ValueError("chunk-overlap must be smaller than max-chars")

    chunks: list[tuple[str, Document]] = []
    chunk_count = (max(len(content) - overlap, 0) + step - 1) // step
    for chunk_index, start in enumerate(range(0, len(content), step)):
        chunk_content = content[start : start + max_chars]
        if not chunk_content:
            break
        metadata = {
            **document.metadata,
            "source_document_id": source_id,
            "chunk_index": chunk_index,
            "chunk_count": chunk_count,
        }
        chunks.append(
            (
                f"{source_id}:chunk:{chunk_index}",
                Document(page_content=chunk_content, metadata=metadata),
            )
        )
        if start + max_chars >= len(content):
            break
    return chunks


def add_with_retry(
    store: QdrantDocumentStore,
    documents: list[Document],
    source_ids: list[str],
    *,
    max_retries: int,
) -> None:
    for attempt in range(max_retries + 1):
        try:
            store.add_documents(documents, ids=source_ids)
            return
        except Exception as exc:
            message = str(exc)
            rate_limited = "429" in message or "RESOURCE_EXHAUSTED" in message
            if not rate_limited or attempt >= max_retries:
                raise
            wait_seconds = min(60 * (2**attempt), 300)
            print(
                f"Embedding quota reached; retrying in {wait_seconds} seconds "
                f"({attempt + 1}/{max_retries})",
                flush=True,
            )
            time.sleep(wait_seconds)


def main() -> None:
    args = parse_args()
    if args.batch_size <= 0:
        raise ValueError("batch-size must be positive")
    if args.max_chars <= 0 or args.chars_per_minute <= 0:
        raise ValueError("max-chars and chars-per-minute must be positive")
    client = chromadb.PersistentClient(path=args.chroma_path)
    collection_names = [collection.name for collection in client.list_collections()]
    if args.chroma_collection not in collection_names:
        available = ", ".join(collection_names) or "(none)"
        raise RuntimeError(
            f"Chroma collection '{args.chroma_collection}' was not found. Available: {available}"
        )

    collection = client.get_collection(args.chroma_collection)
    result = collection.get(include=["documents", "metadatas"])
    rows = [
        (source_id, Document(page_content=content, metadata=metadata or {}))
        for source_id, content, metadata in zip(
            result.get("ids") or [],
            result.get("documents") or [],
            result.get("metadatas") or [],
            strict=True,
        )
        if content
    ]
    if not 0 <= args.start_index <= len(rows):
        raise ValueError(f"start-index must be between 0 and {len(rows)}")

    pending_rows: list[tuple[str, Document]] = []
    for source_id, document in rows[args.start_index :]:
        pending_rows.extend(
            split_document(
                source_id,
                document,
                max_chars=args.max_chars,
                overlap=args.chunk_overlap,
            )
        )
    if not 0 <= args.start_vector_index <= len(pending_rows):
        raise ValueError(
            f"start-vector-index must be between 0 and {len(pending_rows)}"
        )
    total_vector_documents = len(pending_rows)
    pending_rows = pending_rows[args.start_vector_index :]
    source_ids = [source_id for source_id, _ in pending_rows]
    documents = [document for _, document in pending_rows]

    embedding_provider = os.getenv("EMBEDDING_PROVIDER", "google").lower()
    embeddings = build_embeddings(embedding_provider)
    store = QdrantDocumentStore(
        url=require_env("QDRANT_URL"),
        api_key=require_env("QDRANT_API_KEY"),
        collection_name=os.getenv("QDRANT_COLLECTION", "knu-campus"),
        embeddings=embeddings,
    )

    print(
        f"Embedding provider: {embedding_provider}; "
        f"starting at Chroma index {args.start_index}; "
        f"starting at vector index {args.start_vector_index}; "
        f"{len(documents)}/{total_vector_documents} vector documents remain",
        flush=True,
    )
    for start in range(0, len(documents), args.batch_size):
        end = min(start + args.batch_size, len(documents))
        add_with_retry(
            store,
            documents[start:end],
            source_ids[start:end],
            max_retries=args.max_retries,
        )
        completed = args.start_vector_index + end
        print(
            f"Migrated {completed}/{total_vector_documents} vector documents",
            flush=True,
        )
        if end < len(documents):
            batch_chars = sum(len(document.page_content) for document in documents[start:end])
            paced_delay = (batch_chars / args.chars_per_minute) * 60
            time.sleep(max(args.delay_seconds, paced_delay))

    print("Chroma to Qdrant migration completed")


if __name__ == "__main__":
    main()
