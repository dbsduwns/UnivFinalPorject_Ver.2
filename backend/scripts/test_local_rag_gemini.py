import os
import sys

# 백엔드 최상위 경로를 시스템 패스에 추가하여 app 모듈을 임포트할 수 있게 함
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# .env 파일에서 GOOGLE_API_KEY 로드
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("❌ 에러: .env 파일에 GOOGLE_API_KEY가 설정되어 있지 않습니다.")
    print("구글 AI 스튜디오(https://aistudio.google.com/app/apikey)에서 무료 키를 발급받아주세요.")
    sys.exit(1)

print("⏳ 1. 로컬 임베딩 모델 및 벡터 DB 로드 중...")
embeddings = HuggingFaceEmbeddings(
    model_name="jhgan/ko-sroberta-multitask",
    model_kwargs={'device': 'cuda'},
    encode_kwargs={'normalize_embeddings': True}
)

persist_directory = "./chroma_db"
if not os.path.exists(persist_directory):
    print("❌ 에러: chroma_db 폴더가 없습니다. 먼저 test_local_rag.py를 실행하여 DB를 구축해 주세요.")
    sys.exit(1)

vectorstore = Chroma(persist_directory=persist_directory, embedding_function=embeddings)

# retriever 구성 (검색기)
# k=3: 가장 유사도 높은 문서 3개를 찾아옴
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
print("✅ 벡터 DB 연결 성공!")

print("⏳ 2. 제미나이(Gemini) LLM 설정 중...")
# gemini-flash-latest 모델은 빠르고 비용(무료 티어) 면에서 가장 효율적인 최신 모델입니다.
llm = ChatGoogleGenerativeAI(model="gemini-flash-latest", temperature=0.2)
print("✅ 제미나이 연결 성공!")

# 3. 프롬프트 (Prompt) 템플릿 작성
# 검색된 문서를 바탕으로 질문에 대답하도록 AI에게 지시문을 내립니다.
prompt_template = """당신은 강남대학교 통합 앱(KNU Campus Life)의 친절하고 정확한 공식 챗봇입니다.
오직 아래 제공된 [참고 문서]의 내용만을 바탕으로 [사용자 질문]에 답변해야 합니다.
만약 [참고 문서]에 질문과 관련된 내용이 전혀 없다면, "죄송합니다. 해당 내용에 대한 정보를 찾을 수 없습니다."라고만 대답하세요. 지어내거나 외부 지식을 사용하지 마세요.
답변은 읽기 쉽고 간결하게 작성해주세요.

[참고 문서]:
{context}

[사용자 질문]:
{question}

[답변]:"""

prompt = PromptTemplate.from_template(prompt_template)

# 문서들을 하나의 문자열로 합쳐주는 함수 (Context용)
def format_docs(docs):
    return "\n\n".join(f"출처: {doc.metadata.get('source', '알수없음')}\n내용: {doc.page_content}" for doc in docs)

# 4. RAG 체인(Chain) 생성
# 흐름: 질문 -> Retriever(검색) -> Context 생성 -> 프롬프트 조립 -> 제미나이 응답 -> 문자열 파싱
rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

print("-" * 50)
print("🤖 제미나이가 탑재된 RAG 챗봇 테스트를 시작합니다.")
print("-" * 50)

queries = [
    "이번 학기 기말고사는 언제야?",
    "성적 우수 장학금을 받으려면 학점이 몇 점 넘어야 해?",
    "셔틀버스 시간표 알아?", # (현재 DB에 없으므로 "모른다"고 답해야 정상입니다)
]

for query in queries:
    print(f"\n👤 질문: {query}")
    print("⏳ 답변 생성 중...")
    
    # 체인 실행
    response = rag_chain.invoke(query)
    
    print(f"🤖 챗봇 답변:\n{response}")
