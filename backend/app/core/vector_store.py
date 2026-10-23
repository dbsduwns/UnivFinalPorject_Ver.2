from __future__ import annotations

import asyncio
import json
import re
import uuid
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from app.core.retrieval_filters import build_qdrant_filter
from qdrant_client.models import MatchValue

if TYPE_CHECKING:
    from langchain_core.documents import Document


class QdrantDocumentStore:
    """Small LangChain-compatible adapter for the managed Qdrant service."""

    EMBEDDING_BATCH_DOCUMENTS = 32
    EMBEDDING_BATCH_CHARACTERS = 30_000

    def __init__(
        self,
        *,
        url: str,
        api_key: str,
        collection_name: str,
        embeddings: Any,
        search_limit: int = 5,
        lexical_weight: float = 0.25,
        vector_weight: float = 0.75,
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
        if lexical_weight < 0 or vector_weight < 0 or lexical_weight + vector_weight <= 0:
            raise ValueError("retrieval weights must be non-negative with a positive sum")
        weight_total = lexical_weight + vector_weight
        self.lexical_weight = lexical_weight / weight_total
        self.vector_weight = vector_weight / weight_total
        self._text_index_ready = False

    def collection_status(self) -> dict[str, int | bool]:
        """현재 검색 대상 컬렉션의 존재 여부와 저장된 point 수를 확인합니다."""
        if not self.client.collection_exists(self.collection_name):
            return {"exists": False, "points_count": 0}

        collection = self.client.get_collection(self.collection_name)
        return {
            "exists": True,
            "points_count": int(collection.points_count or 0),
        }

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
    def _search_keywords (query: str) -> list[str]:
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

    @staticmethod
    def _lexical_rank_key(query: str, point: Any) -> tuple[int, int, int]:
        """Rank Qdrant text-filter matches by coverage and title specificity."""
        payload = point.payload or {}
        metadata = payload.get("metadata") or {}
        title = str(metadata.get("title") or metadata.get("event") or "").casefold()
        content = str(payload.get("page_content") or "").casefold()
        keywords = QdrantDocumentStore._search_keywords(query)
        title_matches = sum(keyword.casefold() in title for keyword in keywords)
        content_matches = sum(keyword.casefold() in content for keyword in keywords)
        compact_query = "".join(query.split()).casefold()
        compact_title = "".join(title.split())
        exact_title = int(bool(compact_query) and compact_query in compact_title)
        return (exact_title, title_matches, content_matches)

    def _lexical_search(
        self,
        query: str,
        *,
        limit: int | None = None,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[Any]:
        from qdrant_client.models import FieldCondition, Filter, MatchText

        keywords = self._search_keywords(query)
        if not keywords:
            return []
        search_limit = limit or self.search_limit

        metadata_conditions = [
            FieldCondition(
                key=f"metadata.{field}",
                match=MatchValue(value=value),
            )
            for field, value in (metadata_filter or {}).items()
        ]

        text_conditions = [
            FieldCondition(
                key="page_content",
                match=MatchText(text=keyword)
            )
            for keyword in keywords
        ]

        strict_filter = Filter(
            must=[*metadata_conditions, *text_conditions],
        )


        def matches_metadata(point: Any) -> bool:
            metadata = (point.payload or {}).get("metadata") or {}
            return all(
                metadata.get(field) == value
                for field, value in (metadata_filter or {}).items()
            )

        records, _ = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=strict_filter,
            limit=search_limit,
            with_payload=True,
            with_vectors=False,
        )
        records = [point for point in records if matches_metadata(point)]
        if records or len(text_conditions) == 1:
            return sorted(
                records,
                key=lambda point: self._lexical_rank_key(query, point),
                reverse=True,
            )

        fallback_filter = Filter(
            must=metadata_conditions,
            should=text_conditions,
        )

        records, _ = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=fallback_filter,
            limit=search_limit,
            with_payload=True,
            with_vectors=False,
        )
        records = [point for point in records if matches_metadata(point)]
        return sorted(
            records,
            key=lambda point: self._lexical_rank_key(query, point),
            reverse=True,
        )

    @staticmethod
    def _weighted_rrf(
        lexical_points: Sequence[Any],
        vector_points: Sequence[Any],
        *,
        limit: int,
        lexical_weight: float = 0.25,
        vector_weight: float = 0.75,
        rank_constant: int = 60,
    ) -> list[Any]:
        """Fuse ranked results while keeping dense retrieval as the primary signal."""
        scores: dict[str, float] = {}
        points_by_id: dict[str, Any] = {}
        best_rank: dict[str, int] = {}
        for weight, points in (
            (lexical_weight, lexical_points),
            (vector_weight, vector_points),
        ):
            for rank, point in enumerate(points, start=1):
                point_id = str(point.id)
                points_by_id.setdefault(point_id, point)
                best_rank[point_id] = min(best_rank.get(point_id, rank), rank)
                scores[point_id] = scores.get(point_id, 0.0) + weight / (
                    rank_constant + rank
                )
        ranked_ids = sorted(
            scores,
            key=lambda point_id: (-scores[point_id], best_rank[point_id], point_id),
        )
        return [points_by_id[point_id] for point_id in ranked_ids[:limit]]

    def add_documents(
        self,
        documents: Sequence[Document],
        ids: Sequence[str] | None = None,
    ) -> None:
        from qdrant_client.models import PointStruct

        if not documents:
            return

        if ids is not None and len(ids) != len(documents):
            raise ValueError("ids and documents must have the same length")
        raw_ids = list(ids) if ids is not None else [self._document_id(doc) for doc in documents]
        point_ids = [self._point_id(point_id) for point_id in raw_ids]

        batch_start = 0
        while batch_start < len(documents):
            batch_end = batch_start
            batch_characters = 0
            while batch_end < len(documents):
                document_characters = len(documents[batch_end].page_content)
                exceeds_document_limit = (
                    batch_end - batch_start >= self.EMBEDDING_BATCH_DOCUMENTS
                )
                exceeds_character_limit = (
                    batch_end > batch_start
                    and batch_characters + document_characters
                    > self.EMBEDDING_BATCH_CHARACTERS
                )
                if exceeds_document_limit or exceeds_character_limit:
                    break
                batch_characters += document_characters
                batch_end += 1

            batch_documents = documents[batch_start:batch_end]
            texts = [document.page_content for document in batch_documents]
            vectors = self.embeddings.embed_documents(texts)
            if not vectors:
                raise RuntimeError("임베딩 API가 빈 결과를 반환했습니다.")
            if len(vectors) != len(batch_documents):
                raise RuntimeError("임베딩 결과 수가 요청한 문서 수와 다릅니다.")

            self._ensure_collection(len(vectors[0]))
            points = [
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "page_content": document.page_content,
                        "metadata": self._json_safe_metadata(document.metadata),
                    },
                )
                for point_id, vector, document in zip(
                    point_ids[batch_start:batch_end],
                    vectors,
                    batch_documents,
                    strict=True,
                )
            ]
            self.client.upsert(
                collection_name=self.collection_name,
                points=points,
                wait=True,
            )
            batch_start = batch_end

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
        return self.search_diagnostics(query)["hybrid"]

    def search_diagnostics(
        self,
        query: str,
        *,
        ensure_text_index: bool = True,
        metadata_filter: dict[str, Any] | None = None,
        query_vector: Sequence[float] | None = None,
    ) -> dict[str, list[Document]]:
        """Return individual, legacy, and weighted-fusion retrieval results."""
        from langchain_core.documents import Document

        if not self.client.collection_exists(self.collection_name):
            return {
                "lexical": [],
                "vector": [],
                "legacy_hybrid": [],
                "hybrid": [],
            }

        if ensure_text_index:
            self._ensure_text_index()
        else:
            collection = self.client.get_collection(self.collection_name)
            if "page_content" not in collection.payload_schema:
                raise RuntimeError(
                    "Qdrant page_content text index is missing; evaluation will not modify the collection"
                )
        lexical_candidate_limit = (
            1_000 if metadata_filter else max(self.search_limit * 4, 20)
        )
        lexical_points = self._lexical_search(
            query,
            limit=lexical_candidate_limit,
            metadata_filter=metadata_filter,
        )
        vector = (
            list(query_vector)
            if query_vector is not None
            else self.embeddings.embed_query(query)
        )
        query_filter = build_qdrant_filter(metadata_filter)
        response = self.client.query_points(
            collection_name=self.collection_name,
            query=vector,
            query_filter=query_filter,
            limit=1_000 if metadata_filter else self.search_limit,
            with_payload=True,
        )
        vector_points = list(response.points)
        if metadata_filter:
            vector_points = [
                point
                for point in vector_points
                if all(
                    ((point.payload or {}).get("metadata") or {}).get(field) == value
                    for field, value in metadata_filter.items()
                )
            ]
        def to_documents(points: Sequence[Any]) -> list[Document]:
            documents: list[Document] = []
            seen_ids: set[str] = set()
            for point in points:
                point_id = str(point.id)
                if point_id in seen_ids:
                    continue
                seen_ids.add(point_id)
                payload = point.payload or {}
                page_content = payload.get("page_content")
                if not page_content:
                    continue
                metadata = dict(payload.get("metadata") or {})
                metadata["_retrieval_point_id"] = point_id
                documents.append(Document(page_content=str(page_content), metadata=metadata))
                if len(documents) >= self.search_limit:
                    break
            return documents

        lexical = to_documents(lexical_points)
        vector = to_documents(vector_points)
        legacy_hybrid = to_documents(
            [
                *lexical_points[: self.search_limit],
                *vector_points[: self.search_limit],
            ]
        )
        dense_top_points = vector_points[: self.search_limit]
        dense_top_ids = {str(point.id) for point in dense_top_points}
        lexical_agreements = [
            point for point in lexical_points if str(point.id) in dense_top_ids
        ]
        hybrid_points = self._weighted_rrf(
            lexical_agreements,
            dense_top_points,
            limit=self.search_limit,
            lexical_weight=self.lexical_weight,
            vector_weight=self.vector_weight,
        )
        hybrid = to_documents(hybrid_points)
        return {
            "lexical": lexical,
            "vector": vector,
            "legacy_hybrid": legacy_hybrid,
            "hybrid": hybrid,
        }

    def metadata_coverage(self, *, page_size: int = 256) -> dict[str, Any]:
        """Inspect payload metadata coverage without changing the collection."""
        if not self.client.collection_exists(self.collection_name):
            raise RuntimeError(f"Qdrant collection does not exist: {self.collection_name}")

        by_source: dict[str, dict[str, Any]] = {}
        offset = None
        total = 0
        while True:
            points, offset = self.client.scroll(
                collection_name=self.collection_name,
                limit=page_size,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            for point in points:
                payload = point.payload or {}
                metadata = payload.get("metadata") or {}
                if not isinstance(metadata, dict):
                    metadata = {}
                source = str(metadata.get("source") or "(출처 없음)")
                bucket = by_source.setdefault(source, {"count": 0, "fields": {}})
                bucket["count"] += 1
                total += 1
                for key in set(bucket["fields"]) | set(metadata):
                    field = bucket["fields"].setdefault(key, {"present": 0, "values": {}})
                    value = metadata.get(key)
                    if value is not None and value != "":
                        field["present"] += 1
                        label = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
                        field["values"][label] = field["values"].get(label, 0) + 1
            if offset is None:
                break

        for bucket in by_source.values():
            for field in bucket["fields"].values():
                field["coverage"] = field["present"] / bucket["count"] if bucket["count"] else 0
                sorted_values = sorted(
                    field["values"].items(), key=lambda item: (-item[1], item[0])
                )
                field["distinct_value_count"] = len(sorted_values)
                field["values"] = dict(sorted_values[:100])
        return {"total_points": total, "by_source": by_source}

    def iter_documents(self, *, page_size: int = 256):
        """Yield indexed payloads for diagnostics without fetching stored vectors."""
        from langchain_core.documents import Document

        if not self.client.collection_exists(self.collection_name):
            raise RuntimeError(f"Qdrant collection does not exist: {self.collection_name}")
        offset = None
        while True:
            points, offset = self.client.scroll(
                collection_name=self.collection_name,
                limit=page_size,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            for point in points:
                payload = point.payload or {}
                content = payload.get("page_content")
                if not content:
                    continue
                metadata = dict(payload.get("metadata") or {})
                metadata["_retrieval_point_id"] = str(point.id)
                yield Document(page_content=str(content), metadata=metadata)
            if offset is None:
                break

    async def ainvoke(self, query: str) -> list[Document]:
        return await asyncio.to_thread(self._search, query)

    
    async def asearch(
            self,
            query: str,
            *,
            metadata_filter: dict | None = None,
    ):
        return await asyncio.to_thread(
            lambda: self.search_diagnostics(
                query,
                metadata_filter=metadata_filter,
            )["hybrid"]
        )
