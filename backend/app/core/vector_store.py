from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from langchain_core.documents import Document


class QdrantDocumentStore:
    """Small LangChain-compatible adapter for the managed Qdrant service."""

    def __init__(
        self,
        *,
        url: str,
        api_key: str,
        collection_name: str,
        embeddings: Any,
        search_limit: int = 5,
    ) -> None:
        from qdrant_client import QdrantClient

        self.client = QdrantClient(
            url=url,
            api_key=api_key,
            prefer_grpc=False,
            timeout=30,
        )
        self.collection_name = collection_name
        self.embeddings = embeddings
        self.search_limit = search_limit

    @staticmethod
    def _document_id(document: Document) -> str:
        identity = json.dumps(
            {
                "page_content": document.page_content,
                "metadata": document.metadata,
            },
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        )
        return str(uuid.uuid5(uuid.NAMESPACE_URL, identity))

    @staticmethod
    def _point_id(value: str) -> str:
        try:
            return str(uuid.UUID(str(value)))
        except ValueError:
            return str(uuid.uuid5(uuid.NAMESPACE_URL, str(value)))

    @staticmethod
    def _json_safe_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
        return json.loads(json.dumps(metadata, ensure_ascii=False, default=str))

    def _ensure_collection(self, vector_size: int) -> None:
        from qdrant_client.models import Distance, VectorParams

        if self.client.collection_exists(self.collection_name):
            return

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )

    def add_documents(
        self,
        documents: Sequence[Document],
        ids: Sequence[str] | None = None,
    ) -> None:
        from qdrant_client.models import PointStruct

        if not documents:
            return

        texts = [document.page_content for document in documents]
        vectors = self.embeddings.embed_documents(texts)
        if not vectors:
            return

        self._ensure_collection(len(vectors[0]))
        if ids is not None and len(ids) != len(documents):
            raise ValueError("ids and documents must have the same length")
        raw_ids = list(ids) if ids is not None else [self._document_id(doc) for doc in documents]
        point_ids = [self._point_id(point_id) for point_id in raw_ids]
        points = [
            PointStruct(
                id=point_id,
                vector=vector,
                payload={
                    "page_content": document.page_content,
                    "metadata": self._json_safe_metadata(document.metadata),
                },
            )
            for point_id, vector, document in zip(point_ids, vectors, documents, strict=True)
        ]
        self.client.upsert(collection_name=self.collection_name, points=points, wait=True)

    def _search(self, query: str) -> list[Document]:
        from langchain_core.documents import Document

        if not self.client.collection_exists(self.collection_name):
            return []

        vector = self.embeddings.embed_query(query)
        response = self.client.query_points(
            collection_name=self.collection_name,
            query=vector,
            limit=self.search_limit,
            with_payload=True,
        )
        documents: list[Document] = []
        for point in response.points:
            payload = point.payload or {}
            page_content = payload.get("page_content")
            if not page_content:
                continue
            documents.append(
                Document(
                    page_content=str(page_content),
                    metadata=payload.get("metadata") or {},
                )
            )
        return documents

    async def ainvoke(self, query: str) -> list[Document]:
        return await asyncio.to_thread(self._search, query)
