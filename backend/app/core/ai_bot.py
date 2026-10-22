from __future__ import annotations

import os
from collections import Counter
from datetime import datetime
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from app.services.academic_calendar import (
    build_academic_calendar_answer,
    build_academic_calendar_context,
    is_academic_calendar_query,
)
from app.services.timetable_context import is_timetable_only_query

if TYPE_CHECKING:
    from langchain_core.documents import Document


load_dotenv()

SEOUL_TIMEZONE = ZoneInfo("Asia/Seoul")
DEFAULT_EMBEDDING_PROVIDER = "cloudflare"
DEFAULT_VECTOR_STORE_PROVIDER = "qdrant"
DEFAULT_LLM_PROVIDER = "cloudflare"
DEFAULT_QDRANT_COLLECTION = "knu-campus-bge-m3"
DEFAULT_QDRANT_SEARCH_LIMIT = 8

NOTICE_QUERY_KEYWORDS = (
    "공지",
    "공지사항",
    "장학",
    "취업",
    "창업",
    "상담",
    "모집",
    "신청",
)

QUERY_REWRITE_CUES = (
    "그거", "그건", "그 일정", "그 내용", "그 날짜", "그 시간", "거기는",
    "거기서", "아까", "방금", "위 내용", "더 자세히", "다시 설명", "그럼", "그리고",
)


class CampusAIBot:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            instance = super().__new__(cls)
            instance.is_initialized = False
            instance.indexing_ready = False
            instance.embeddings = None
            instance.vectorstore = None
            instance.retriever = None
            instance.llm = None
            cls._instance = instance
        return cls._instance

    def initialize(self) -> bool:
        """Cloudflare LLM/임베딩과 Qdrant 검색기를 지연 초기화합니다."""
        if self.is_initialized:
            return True

        # 서버 메모리를 절약하기 위해 실제 사용 시점에만 무거운 모듈을 가져옵니다.
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import PromptTemplate

        from app.core.ai_providers import build_chat_model, build_embeddings

        self.is_initialized = False
        self.indexing_ready = False
        self.embeddings = None
        self.vectorstore = None
        self.retriever = None
        self.llm = None

        embedding_provider = os.getenv(
            "EMBEDDING_PROVIDER", DEFAULT_EMBEDDING_PROVIDER
        ).lower()
        print(f"🤖 [AI Bot] 임베딩 로드 중 ({embedding_provider})...", flush=True)
        try:
            self.embeddings = build_embeddings(embedding_provider)
        except Exception as exc:
            print(f"❌ [AI Bot] 임베딩 모델 로드 실패: {exc}", flush=True)
            return False

        vector_store_provider = os.getenv(
            "VECTOR_STORE_PROVIDER", DEFAULT_VECTOR_STORE_PROVIDER
        ).lower()
        print(f"🤖 [AI Bot] 벡터 DB 연결 중 ({vector_store_provider})...", flush=True)
        try:
            if vector_store_provider == "qdrant":
                from app.core.vector_store import QdrantDocumentStore

                qdrant_url = os.getenv("QDRANT_URL")
                qdrant_api_key = os.getenv("QDRANT_API_KEY")
                if not qdrant_url or not qdrant_api_key:
                    raise ValueError("QDRANT_URL과 QDRANT_API_KEY가 필요합니다.")

                collection_name = os.getenv(
                    "QDRANT_COLLECTION", DEFAULT_QDRANT_COLLECTION
                )
                search_limit = int(
                    os.getenv("QDRANT_SEARCH_LIMIT", str(DEFAULT_QDRANT_SEARCH_LIMIT))
                )
                self.vectorstore = QdrantDocumentStore(
                    url=qdrant_url,
                    api_key=qdrant_api_key,
                    collection_name=collection_name,
                    embeddings=self.embeddings,
                    search_limit=search_limit,
                )
                collection_status = self.vectorstore.collection_status()
                if collection_status["exists"]:
                    print(
                        "✅ [AI Bot] Qdrant 컬렉션 확인 완료: "
                        f"collection={collection_name}, "
                        f"points={collection_status['points_count']}",
                        flush=True,
                    )
                else:
                    print(
                        "⚠️ [AI Bot] Qdrant 컬렉션이 아직 없습니다: "
                        f"collection={collection_name}",
                        flush=True,
                    )
                self.retriever = self.vectorstore
            elif vector_store_provider == "chroma":
                from pathlib import Path

                from langchain_chroma import Chroma

                backend_dir = Path(__file__).resolve().parents[2]
                persist_directory = str(backend_dir / "chroma_db")
                print(f"🤖 [AI Bot] 벡터 DB 경로: {persist_directory}", flush=True)
                self.vectorstore = Chroma(
                    persist_directory=persist_directory,
                    embedding_function=self.embeddings,
                )
                self.retriever = self.vectorstore.as_retriever(
                    search_kwargs={"k": DEFAULT_QDRANT_SEARCH_LIMIT}
                )
            else:
                raise ValueError(
                    f"지원하지 않는 VECTOR_STORE_PROVIDER: {vector_store_provider}"
                )
            self.indexing_ready = self.vectorstore is not None
        except Exception as exc:
            print(f"❌ [AI Bot] 벡터 DB 로드 실패: {exc}", flush=True)
            self.vectorstore = None
            self.retriever = None

        llm_provider = os.getenv("LLM_PROVIDER", DEFAULT_LLM_PROVIDER).lower()
        print(f"🤖 [AI Bot] LLM 설정 중 ({llm_provider})...", flush=True)
        try:
            self.llm = build_chat_model(llm_provider)
        except Exception as exc:
            print(f"❌ [AI Bot] LLM 설정 실패: {exc}", flush=True)
            self.llm = None

        answer_template = """당신은 강남대학교 캠퍼스 안내 AI 도우미입니다.
제공된 Context를 근거로 사용자의 질문에 정확하고 친절하게 답변하세요.

### 지침
1. Context에 있는 공지사항과 공식 학사일정을 최우선 근거로 사용하세요.
2. 공지사항은 제목, 카테고리, 게시일을 구분하고 서로 다른 공지의 내용을 합치지 마세요.
3. 학사일정은 시작일과 종료일을 정확히 구분하세요.
4. Context에 없는 날짜, 자격, 신청 방법이나 링크를 추측하지 마세요.
5. 근거가 부족하면 "확인할 수 있는 정보가 없습니다"라고 명확히 안내하세요.
6. 학생에게 설명하듯 자연스러운 "해요"체를 사용하세요.

# 오늘 날짜
{current_date}

# Context
{context}

# Question
{question}

# Answer (Korean)"""
        self.prompt = PromptTemplate.from_template(answer_template)

        rewrite_template = """사용자의 질문을 강남대학교 정보 검색에 적합한 한 문장으로 정리하세요.
원래 질문의 의도를 바꾸지 말고, 공지사항 질문을 학사일정 질문으로 바꾸지 마세요.
고유명사, 공지 제목의 핵심어, 날짜, 학기, 장학·모집·시험 등의 구분을 반드시 보존하세요.
설명 없이 검색 문장만 출력하세요.

사용자 질문: {question}
검색 문장:"""
        self.rewrite_prompt = PromptTemplate.from_template(rewrite_template)

        if self.retriever and self.llm:
            self.rewrite_chain = self.rewrite_prompt | self.llm | StrOutputParser()
            self.answer_chain = self.prompt | self.llm | StrOutputParser()
            self.is_initialized = True
            print("✅ [AI Bot] 초기화 완료!", flush=True)
        else:
            print(
                "⚠️ [AI Bot] 일부 구성 요소가 로드되지 않아 답변 체인을 구성할 수 없습니다.",
                flush=True,
            )
        return self.is_initialized

    def add_documents(self, documents: list[Document]) -> None:
        """문서를 임베딩하여 현재 챗봇과 동일한 벡터 DB에 저장합니다."""
        if not documents:
            return
        if not self.indexing_ready:
            self.initialize()
        if not self.vectorstore:
            raise RuntimeError("벡터 DB가 준비되지 않아 문서를 저장할 수 없습니다.")

        self.vectorstore.add_documents(documents)
        print(
            f"✅ [AI Bot] {len(documents)}개의 문서가 벡터 DB에 추가되었습니다.",
            flush=True,
        )

    @staticmethod
    def _document_source(document: Document) -> str:
        return str(document.metadata.get("source") or "unknown")

    @staticmethod
    def _document_identity(document: Document) -> tuple[str, str, str]:
        metadata = document.metadata
        return (
            str(metadata.get("source") or ""),
            str(metadata.get("title") or metadata.get("event") or ""),
            document.page_content,
        )

    @staticmethod
    def _needs_query_rewrite(question: str) -> bool:
        """Avoid an extra model call for self-contained, specific questions."""
        normalized = " ".join(question.split())
        compact = normalized.replace(" ", "")
        return len(compact) <= 5 or any(cue in normalized for cue in QUERY_REWRITE_CUES)

    def _rank_documents(self, documents: list[Document], question: str) -> list[Document]:
        academic_query = is_academic_calendar_query(question)
        notice_query = any(keyword in question for keyword in NOTICE_QUERY_KEYWORDS)

        def priority(document: Document) -> tuple[int, str]:
            source = self._document_source(document)
            if academic_query and source == "학사일정":
                return (0, source)
            if notice_query and source == "공지사항":
                return (0, source)
            if source in {"공지사항", "학사일정"}:
                return (1, source)
            return (2, source)

        return sorted(documents, key=priority)

    def _format_documents(self, documents: list[Document]) -> str:
        if not documents:
            return ""

        lines = ["[Qdrant 검색 문서]"]
        for index, document in enumerate(documents, start=1):
            metadata = document.metadata
            source = self._document_source(document)
            title = metadata.get("title") or metadata.get("event") or ""
            lines.append(f"{index}. 출처: {source}")
            if title:
                lines.append(f"   제목/행사: {title}")
            if metadata.get("category"):
                lines.append(f"   카테고리: {metadata['category']}")
            if metadata.get("published_at"):
                lines.append(f"   게시일: {metadata['published_at']}")
            if metadata.get("start_date") or metadata.get("end_date"):
                lines.append(
                    "   일정: "
                    f"{metadata.get('start_date', '')} ~ {metadata.get('end_date', '')}"
                )
            if metadata.get("source_url"):
                lines.append(f"   원문: {metadata['source_url']}")
            lines.append(document.page_content)
        return "\n".join(lines)

    async def _retrieve_documents(
        self,
        question: str,
        rewritten_question: str | None,
    ) -> list[Document]:
        if not self.retriever:
            return []

        retrieval_query = question.strip()
        rewritten = (rewritten_question or "").strip()
        if rewritten and rewritten != retrieval_query:
            # 원 질문의 정확한 고유명사와 재작성 질문의 검색 보강어를 한 번의 검색에 함께 사용합니다.
            retrieval_query = f"{retrieval_query}\n검색 보강: {rewritten}"

        try:
            retrieved = await self.retriever.ainvoke(retrieval_query)
        except Exception as exc:
            print(f"❌ [AI Bot] Qdrant 검색 실패: {exc}", flush=True)
            return []

        unique_documents: list[Document] = []
        seen: set[tuple[str, str, str]] = set()
        for document in retrieved:
            identity = self._document_identity(document)
            if identity in seen:
                continue
            seen.add(identity)
            unique_documents.append(document)

        ranked = self._rank_documents(unique_documents, question)
        source_counts = Counter(self._document_source(document) for document in ranked)
        print(
            "🔎 [AI Bot] Qdrant 검색 완료: "
            f"query={question!r}, documents={len(ranked)}, "
            f"sources={dict(source_counts)}",
            flush=True,
        )
        for rank, document in enumerate(ranked, start=1):
            metadata = document.metadata
            title = metadata.get("title") or metadata.get("event") or "(제목 없음)"
            source_url = metadata.get("source_url") or "(URL 없음)"
            preview = " ".join(document.page_content.split())[:160]
            print(
                "📄 [AI Bot] 검색 문서: "
                f"rank={rank}, source={self._document_source(document)!r}, "
                f"title={title!r}, url={source_url!r}, preview={preview!r}",
                flush=True,
            )
        return ranked

    async def build_context(
        self,
        question: str,
        rewritten_question: str | None = None,
        personal_context: str | None = None,
    ) -> str:
        """Qdrant 검색 결과를 우선 사용하고 정적 학사일정은 fallback으로만 사용합니다."""
        context_sections: list[str] = []
        timetable_only_query = bool(personal_context) and is_timetable_only_query(question)
        if timetable_only_query:
            documents = []
            print("[AI Bot] 시간표 전용 질문: Qdrant 검색 생략", flush=True)
        else:
            documents = await self._retrieve_documents(question, rewritten_question)

        if documents:
            context_sections.append(self._format_documents(documents))

        if is_academic_calendar_query(question):
            has_qdrant_calendar = any(
                self._document_source(document) == "학사일정"
                for document in documents
            )
            if not has_qdrant_calendar:
                academic_context = build_academic_calendar_context(question)
                if academic_context:
                    print(
                        "⚠️ [AI Bot] Qdrant 학사일정 검색 결과가 없어 정적 일정 fallback을 사용합니다.",
                        flush=True,
                    )
                    context_sections.append(academic_context)

        if personal_context:
            context_sections.append(personal_context)

        return (
            "\n\n".join(context_sections)
            if context_sections
            else "검색된 정보가 없습니다."
        )

    async def ask(
        self,
        question: str,
        personal_context: str | None = None,
    ) -> str:
        if not self.is_initialized:
            print("🤖 [AI Bot] 초기화를 시작합니다...", flush=True)
            if not self.initialize():
                return "AI 엔진이 아직 준비되지 않았습니다."

        try:
            print(f"🔍 [AI Bot] 원본 질문: {question}", flush=True)
            try:
                rewritten_question = (
                    await self.rewrite_chain.ainvoke({"question": question})
                    if self._needs_query_rewrite(question)
                    else question
                )
            except Exception as exc:
                print(
                    f"⚠️ [AI Bot] 질문 재작성 실패, 원본 질문을 사용합니다: {exc}",
                    flush=True,
                )
                rewritten_question = question
            print(f"🔄 [AI Bot] 검색 질문: {rewritten_question}", flush=True)

            context = await self.build_context(
                question,
                rewritten_question,
                personal_context=personal_context,
            )
            print(
                f"📚 [AI Bot] Context 구성 완료: {len(context)}자",
                flush=True,
            )

            response = await self.answer_chain.ainvoke(
                {
                    "context": context,
                    "question": question,
                    "current_date": datetime.now(SEOUL_TIMEZONE).strftime("%Y-%m-%d"),
                }
            )
            print("✅ [AI Bot] 답변 생성 완료", flush=True)
            return response
        except Exception as exc:
            print(f"❌ [AI Bot] 질문 처리 중 오류 발생: {exc}", flush=True)
            import traceback

            traceback.print_exc()
            academic_calendar_answer = build_academic_calendar_answer(question)
            if academic_calendar_answer:
                return academic_calendar_answer
            return "상담 도중 오류가 발생했습니다."


campus_ai_bot = CampusAIBot()
