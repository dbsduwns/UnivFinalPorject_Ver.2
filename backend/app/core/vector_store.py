from __future__ import annotations

import asyncio
import json
import re
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
        self._text_index_ready = False

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

        if not self.client.collection_exists(self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
        self._ensure_text_index()

    def _ensure_text_index(self) -> None:
        if self._text_index_ready or not self.client.collection_exists(self.collection_name):
            return

        from qdrant_client.models import TextIndexParams, TextIndexType, TokenizerType

        collection = self.client.get_collection(self.collection_name)
        if "page_content" not in collection.payload_schema:
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="page_content",
                field_schema=TextIndexParams(
                    type=TextIndexType.TEXT,
                    tokenizer=TokenizerType.MULTILINGUAL,
                    min_token_len=2,
                    lowercase=True,
                ),
                wait=True,
            )
        self._text_index_ready = True

    @staticmethod
    def _search_keywords(query: str) -> list[str]:
        stopwords = {
            "강남대학교",
            "공지사항",
            "공지",
            "관련",
            "관련된",
            "현재",
            "지금",
            "정보",
            "내용",
            "알려줘",
            "알려주세요",
            "궁금해",
            "질문",
        }
        particles = (
            "으로부터",
            "에서부터",
            "이라고",
            "이라고는",
            "으로",
            "에서",
            "에게",
            "까지",
            "부터",
            "처럼",
            "보다",
            "하고",
            "이나",
            "거나",
            "입니다",
            "인가요",
            "의",
            "은",
            "는",
            "이",
            "가",
            "을",
            "를",
            "과",
            "와",
            "도",
            "만",
            "에",
        )
        keywords: list[str] = []
        for raw_token in re.findall(r"[0-9A-Za-z가-힣]+", query):
            token = raw_token
            for particle in particles:
                if token.endswith(particle) and len(token) > len(particle) + 1:
                    token = token[: -len(particle)]
                    break
            if len(token) < 2 or token in stopwords or token in keywords:
                continue
            keywords.append(token)
        return keywords[:3]

    def _lexical_search(self, query: str) -> list[Any]:
        from qdrant_client.models import FieldCondition, Filter, MatchText

        keywords = self._search_keywords(query)
        if not keywords:
            return []

        conditions = [
            FieldCondition(key="page_content", match=MatchText(text=keyword))
            for keyword in keywords
        ]
        records, _ = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=Filter(must=conditions),
            limit=self.search_limit,
            with_payload=True,
            with_vectors=False,
        )
        if records or len(conditions) == 1:
            return records

        records, _ = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=Filter(should=conditions),
            limit=self.search_limit,
            with_payload=True,
            with_vectors=False,
        )
        return records

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

    def replace_documents_by_source(
        self,
        documents: Sequence[Document],
        *,
        ids: Sequence[str],
        source: str,
    ) -> int:
        """Upsert a complete source snapshot, then remove stale points safely."""

        if len(documents) != len(ids):
            raise ValueError("ids and documents must have the same length")
        if not documents:
            raise ValueError("refusing to replace a source with an empty document set")

        # New points are written first. A failed embedding or upsert therefore leaves the
        # previously indexed snapshot intact.
        self.add_documents(documents, ids=ids)

        from qdrant_client.models import PointIdsList

        expected_ids = {self._point_id(value) for value in ids}
        existing_ids: set[str] = set()
        offset = None
        while True:
            points, offset = self.client.scroll(
                collection_name=self.collection_name,
                limit=256,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            for point in points:
                payload = point.payload or {}
                metadata = payload.get("metadata") or {}
                if isinstance(metadata, dict) and metadata.get("source") == source:
                    existing_ids.add(str(point.id))
            if offset is None:
                break

        stale_ids = sorted(existing_ids - expected_ids)
        if stale_ids:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=PointIdsList(points=stale_ids),
                wait=True,
            )
        return len(stale_ids)

    def _search(self, query: str) -> list[Document]:
        from langchain_core.documents import Document

        if not self.client.collection_exists(self.collection_name):
            return []

        self._ensure_text_index()
        lexical_points = self._lexical_search(query)
        vector = self.embeddings.embed_query(query)
        response = self.client.query_points(
            collection_name=self.collection_name,
            query=vector,
            limit=self.search_limit,
            with_payload=True,
        )
        documents: list[Document] = []
        seen_ids: set[str] = set()
        for point in [*lexical_points, *response.points]:
            point_id = str(point.id)
            if point_id in seen_ids:
                continue
            seen_ids.add(point_id)
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
            if len(documents) >= self.search_limit:
                break
        return documents

    async def ainvoke(self, query: str) -> list[Document]:
        return await asyncio.to_thread(self._search, query)
