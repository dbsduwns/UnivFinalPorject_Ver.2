import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.documents import Document
from datetime import datetime
from dotenv import load_dotenv
from app.services.academic_calendar import (
    build_academic_calendar_answer,
    build_academic_calendar_context,
)

# .env 파일 로드
load_dotenv()

class CampusAIBot:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CampusAIBot, cls).__new__(cls)
            cls._instance.is_initialized = False
        return cls._instance

    def initialize(self):
        if self.is_initialized:
            return

        print("🤖 [AI Bot] 로컬 임베딩 모델 로드 중...")
        try:
            self.embeddings = HuggingFaceEmbeddings(
                model_name="jhgan/ko-sroberta-multitask",
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )
        except Exception as e:
            print(f"❌ [AI Bot] 임베딩 모델 로드 실패: {e}")
            return

        print("🤖 [AI Bot] 벡터 DB(Chroma) 연결 중...")
        from pathlib import Path
        current_file = Path(__file__).resolve()
        backend_dir = current_file.parents[2] 
        persist_directory = str(backend_dir / "chroma_db")
        
        print(f"🤖 [AI Bot] 벡터 DB 경로: {persist_directory}")
        
        try:
            self.vectorstore = Chroma(
                persist_directory=persist_directory,
                embedding_function=self.embeddings
            )
            # 검색 결과 개수(k)를 3에서 5로 늘려 더 많은 문맥을 참고하게 함
            self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 5})
        except Exception as e:
            print(f"❌ [AI Bot] 벡터 DB 로드 실패: {e}")
            self.retriever = None

        print("🤖 [AI Bot] Gemini LLM 설정 중...")
        try:
            api_key = os.getenv("GOOGLE_API_KEY")
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-flash-latest",
                google_api_key=api_key,
                # temperature를 0.7로 높여 더 자연스럽고 풍부한 답변을 유도
                temperature=0.7,
                max_retries=2,
            )
        except Exception as e:
            print(f"❌ [AI Bot] Gemini LLM 설정 실패: {e}")
            self.llm = None

        template = """당신은 강남대학교 캠퍼스 안내 AI 도우미입니다. 
제공된 정보(Context)를 바탕으로 사용자의 질문에 친절하고 상세하게 답변하세요.

### 지침(Instructions):
1. **상세한 안내:** 단순히 사실만 나열하지 말고, 질문과 관련된 유용한 정보가 있다면 함께 포함하여 친절하게 설명해 주세요.
2. **사실 근거:** 답변은 반드시 제공된 # Context의 내용을 기반으로 해야 합니다. 만약 Context의 내용이 질문과 직접적인 연관이 적더라도, 최대한 관련 있는 정보를 찾아 안내해 주세요.
3. **날짜 기준:** 오늘은 {current_date}입니다. 일정에 대한 질문 시, 오늘 날짜를 기준으로 '진행 중'이거나 '다가올' 가장 빠른 일정을 우선적으로 안내하세요.
4. **불확실성 처리:** 답변에 필요한 정보가 Context에 전혀 없는 경우에만 "죄송합니다. 해당 내용에 대한 정보를 찾을 수 없습니다."라고 답변하세요. 이때 대학 홈페이지나 관련 부서의 일반적인 안내가 있다면 덧붙여 주세요.
5. **말투:** 학생들에게 이야기하듯 "해요"체를 사용하며 따뜻하고 친절한 느낌을 유지하세요.

# Context:
{context}

# Question:
{question}

# Answer (Korean):"""

        self.prompt = PromptTemplate.from_template(template)

        # Query Rewrite를 위한 전처리 프롬프트
        rewrite_template = """당신은 사용자의 질문을 검색에 최적화된 형태로 재작성하는 전문가입니다.
사용자의 질문이 모호하거나 문맥이 부족한 경우, '강남대학교 학사일정'과 관련된 구체적인 질문으로 확장하세요.
특히 날짜만 있는 경우 해당 날짜의 일정을 묻는 질문으로 바꾸세요.

사용자 질문: {question}
재작성된 질문 (Korean):"""
        self.rewrite_prompt = PromptTemplate.from_template(rewrite_template)

        if self.retriever and self.llm:
            # 1. 쿼리 재작성 체인
            self.rewrite_chain = self.rewrite_prompt | self.llm | StrOutputParser()
            self.answer_chain = self.prompt | self.llm | StrOutputParser()

            # 2. 메인 RAG 체인
            self.chain = (
                {
                    "context": self.retriever, 
                    "question": RunnablePassthrough(),
                    "current_date": lambda _: datetime.now().strftime('%Y-%m-%d')
                }
                | self.prompt
                | self.llm
                | StrOutputParser()
            )
            self.is_initialized = True
            print("✅ [AI Bot] 초기화 완료!")
        else:
            print("⚠️ [AI Bot] 일부 구성 요소가 로드되지 않아 체인을 구성할 수 없습니다.")

    def add_documents(self, documents: list[Document]):
        if not self.is_initialized:
            self.initialize()
        if self.vectorstore:
            self.vectorstore.add_documents(documents)
            print(f"✅ [AI Bot] {len(documents)}개의 문서가 벡터 DB에 추가되었습니다.")

    def _format_documents(self, documents: list[Document]) -> str:
        if not documents:
            return ""

        lines = ["[검색된 문서]"]
        for idx, doc in enumerate(documents, start=1):
            source = doc.metadata.get("source", "unknown")
            title = doc.metadata.get("title") or doc.metadata.get("event") or ""
            lines.append(f"{idx}. 출처: {source}")
            if title:
                lines.append(f"   제목/행사: {title}")
            lines.append(doc.page_content)
        return "\n".join(lines)

    async def build_context(self, question: str, rewritten_question: str | None = None) -> str:
        context_sections: list[str] = []

        academic_context = build_academic_calendar_context(question)
        # 만약 원본 질문에서 일정을 찾지 못했거나 키워드 매칭이 안 된 경우, 재작성된 질문으로 다시 시도
        if (not academic_context or "찾지 못했습니다" in academic_context) and rewritten_question:
            alt_context = build_academic_calendar_context(rewritten_question)
            if alt_context and "찾지 못했습니다" not in alt_context:
                academic_context = alt_context
        
        if academic_context:
            context_sections.append(academic_context)

        if self.retriever:
            retrieved_docs = await self.retriever.ainvoke(rewritten_question or question)
            retrieved_context = self._format_documents(retrieved_docs)
            if retrieved_context:
                context_sections.append(retrieved_context)

        return "\n\n".join(context_sections) if context_sections else "검색된 정보가 없습니다."

    async def ask(self, question: str) -> str:
        if not self.is_initialized:
            print("🤖 [AI Bot] Not initialized. Initializing now...", flush=True)
            self.initialize()
            if not self.is_initialized:
                return "AI 엔진이 아직 준비되지 않았습니다."
        try:
            # Step 1: Query Rewrite (질문 재작성)
            print(f"🔍 [AI Bot] 원본 질문: {question}", flush=True)
            rewritten_question = await self.rewrite_chain.ainvoke({"question": question})
            print(f"🔄 [AI Bot] 재작성된 질문: {rewritten_question}", flush=True)

            # Step 2: 구조화 학사일정 + 검색 문서 Context 구성
            context = await self.build_context(question, rewritten_question)
            print(f"📚 [AI Bot] Context 구성 완료:\n{context}", flush=True)

            # Step 3: RAG 실행
            print(f"🚀 [AI Bot] Gemini LLM 호출 중...", flush=True)
            response = await self.answer_chain.ainvoke({
                "context": context,
                "question": question,
                "current_date": datetime.now().strftime('%Y-%m-%d'),
            })
            print(f"✅ [AI Bot] 답변 생성 완료", flush=True)
            return response
        except Exception as e:
            print(f"❌ [AI Bot] 질문 처리 중 오류 발생: {e}", flush=True)
            import traceback
            traceback.print_exc()
            academic_calendar_answer = build_academic_calendar_answer(question)
            if academic_calendar_answer:
                return academic_calendar_answer
            return "상담 도중 오류가 발생했습니다."

campus_ai_bot = CampusAIBot()
