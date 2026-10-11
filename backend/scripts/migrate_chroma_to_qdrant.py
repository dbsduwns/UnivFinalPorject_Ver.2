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

import chromadb  # noqa: E402
from langchain_core.documents import Document  # noqa: E402
from langchain_google_genai import GoogleGenerativeAIEmbeddings  # noqa: E402

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
    parser.add_argument("--batch-size", type=int, default=25)
    return parser.parse_args()


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} environment variable is required")
    return value


def main() -> None:
    args = parse_args()
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
    source_ids = [source_id for source_id, _ in rows]
    documents = [document for _, document in rows]

    embeddings = GoogleGenerativeAIEmbeddings(
        model=os.getenv("GOOGLE_EMBEDDING_MODEL", "models/gemini-embedding-001"),
        google_api_key=require_env("GOOGLE_API_KEY"),
    )
    store = QdrantDocumentStore(
        url=require_env("QDRANT_URL"),
        api_key=require_env("QDRANT_API_KEY"),
        collection_name=os.getenv("QDRANT_COLLECTION", "knu-campus"),
        embeddings=embeddings,
    )

    for start in range(0, len(documents), args.batch_size):
        end = min(start + args.batch_size, len(documents))
        store.add_documents(documents[start:end], ids=source_ids[start:end])
        print(f"Migrated {end}/{len(documents)} documents")

    print("Chroma to Qdrant migration completed")


if __name__ == "__main__":
    main()
