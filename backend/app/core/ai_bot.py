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
        # backend/app/core/ai_bot.py -> backend 디렉토리를 찾음
        current_file = Path(__file__).resolve()
        backend_dir = current_file.parents[2] # core -> app -> backend
        persist_directory = str(backend_dir / "chroma_db")
        
        print(f"🤖 [AI Bot] 벡터 DB 경로: {persist_directory}")
        
        try:
            self.vectorstore = Chroma(
                persist_directory=persist_directory,
                embedding_function=self.embeddings
            )
            self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 3})
        except Exception as e:
            print(f"❌ [AI Bot] 벡터 DB 로드 실패: {e}")
            self.retriever = None

        print("🤖 [AI Bot] Gemini LLM 설정 중...")
        try:
            api_key = os.getenv("GOOGLE_API_KEY")
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-flash-latest", # gemini flash 최신 모델 사용
                google_api_key=api_key,
                temperature=0,
                max_retries=2,
            )
        except Exception as e:
            print(f"❌ [AI Bot] Gemini LLM 설정 실패: {e}")
            self.llm = None

        template = """당신은 강남대학교 캠퍼스 안내 AI 도우미입니다. 
제공된 정보(Context)만을 바탕으로 사용자의 질문에 친절하고 정확하게 답변하세요.

### 지침(Instructions):
1. **사실 근거:** 반드시 아래 제공된 # Context의 내용만을 바탕으로 답변하세요. 외부 지식을 활용하지 마세요.
2. **날짜 기준:** 오늘은 {current_date}입니다. 일정에 대한 질문 시, 오늘 날짜를 기준으로 '진행 중'이거나 '다가올' 가장 빠른 일정을 우선적으로 안내하세요.
3. **불확실성 처리:** 답변에 필요한 정보가 Context에 없거나 부족한 경우, "죄송합니다. 해당 내용에 대한 정보를 찾을 수 없습니다."라고 답변하세요. 추가로 확인할 수 있는 대학 홈페이지나 부서 연락처가 Context에 있다면 함께 안내하세요.
4. **스타일:** 학생들에게 답변하듯 친절한 말투를 유지하세요.

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

    async def ask(self, question: str) -> str:
        if not self.is_initialized:
            self.initialize()
            if not self.is_initialized:
                return "AI 엔진이 아직 준비되지 않았습니다."
        try:
            # Step 1: Query Rewrite (질문 재작성)
            print(f"🔍 [AI Bot] 원본 질문: {question}")
            rewritten_question = await self.rewrite_chain.ainvoke({"question": question})
            print(f"🔄 [AI Bot] 재작성된 질문: {rewritten_question}")

            # Step 2: RAG 실행
            response = await self.chain.ainvoke(rewritten_question)
            return response
        except Exception as e:
            print(f"❌ [AI Bot] 질문 처리 중 오류 발생: {e}")
            return "상담 도중 오류가 발생했습니다."

campus_ai_bot = CampusAIBot()
