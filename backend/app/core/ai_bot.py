import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.documents import Document
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
            # 프로젝트 내 테스트 스크립트에서 확인된 모델명인 'gemini-flash-latest'로 수정
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-flash-latest",
                google_api_key=api_key,
                temperature=0,
                max_retries=2,
            )
        except Exception as e:
            print(f"❌ [AI Bot] Gemini LLM 설정 실패: {e}")
            self.llm = None

        template = """당신은 강남대학교 캠퍼스 안내 AI 도우미입니다. 
주어진 검색 결과(Context)를 바탕으로 사용자의 질문에 친절하고 정확하게 답변하세요.
답변할 수 있는 내용이 없다면, "죄송합니다. 해당 내용에 대한 정보를 찾을 수 없습니다."라고 답변하세요.

# Context:
{context}

# Question:
{question}

# Answer (Korean):"""

        self.prompt = PromptTemplate.from_template(template)

        if self.retriever and self.llm:
            self.chain = (
                {"context": self.retriever, "question": RunnablePassthrough()}
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
            response = await self.chain.ainvoke(question)
            return response
        except Exception as e:
            print(f"❌ [AI Bot] 질문 처리 중 오류 발생: {e}")
            return "상담 도중 오류가 발생했습니다."

campus_ai_bot = CampusAIBot()
