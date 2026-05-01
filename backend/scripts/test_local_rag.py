import os
import sys

# 백엔드 최상위 경로를 시스템 패스에 추가하여 app 모듈을 임포트할 수 있게 함
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.notice import Notice

# LangChain 관련 임포트
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

# 1. 로컬 임베딩 모델 설정 (오픈소스 한국어 모델)
# jhgan/ko-sroberta-multitask는 빠르고 가벼워서 로컬 테스트용으로 매우 좋습니다.
print("⏳ 로컬 임베딩 모델 로드 중 (최초 실행 시 다운로드로 인해 시간이 걸릴 수 있습니다)...")
embeddings = HuggingFaceEmbeddings(
    model_name="jhgan/ko-sroberta-multitask",
    model_kwargs={'device': 'cpu'}, # GPU가 있다면 'cuda'로 변경
    encode_kwargs={'normalize_embeddings': True}
)
print("✅ 임베딩 모델 로드 완료!")

# 2. 데이터 수집
documents = []

# 2-1. 공지사항 데이터 DB에서 가져오기
print("⏳ DB에서 공지사항 데이터 수집 중...")
db: Session = SessionLocal()
try:
    notices = db.query(Notice).limit(50).all() # 테스트를 위해 최근 50개만
    for notice in notices:
        # 벡터 DB에 넣을 텍스트 구성
        text_content = f"제목: {notice.title}\n카테고리: {notice.category}\n내용: {notice.content}"
        
        # 메타데이터 (나중에 출처를 밝히거나 필터링할 때 사용)
        metadata = {
            "source": "공지사항",
            "id": notice.id,
            "category": notice.category,
            "url": notice.source_url or ""
        }
        documents.append(Document(page_content=text_content, metadata=metadata))
    print(f"✅ 공지사항 {len(notices)}개 로드 완료!")
finally:
    db.close()

# 2-2. 학사일정 데이터 (현재 DB에 없다면 텍스트로 하드코딩 또는 파일에서 읽기)
print("⏳ 학사일정 및 학칙 임시 데이터 수집 중...")
calendar_text = """
2026학년도 1학기 주요 학사일정:
- 3월 2일(월): 1학기 개강
- 3월 2일(월) ~ 3월 6일(금): 수강신청 정정기간
- 4월 20일(월) ~ 4월 24일(금): 중간고사
- 6월 15일(월) ~ 6월 19일(금): 기말고사
- 6월 22일(월): 하계방학 시작
"""
documents.append(Document(
    page_content=calendar_text, 
    metadata={"source": "학사일정", "period": "2026-1"}
))

# 2-3. 학칙 데이터 (예시)
rules_text = """
강남대학교 주요 학칙:
제 1조(목적): 본 대학교는 기독교 정신과 홍익인간의 이념을 바탕으로 진리를 탐구하고...
제 20조(졸업학점): 각 단과대학별 졸업 이수 학점은 130학점 이상으로 하되, 사범대학은 140학점 이상으로 한다.
제 35조(장학금): 성적 우수 장학금은 직전 학기 15학점 이상을 이수하고 평점평균이 3.5 이상인 자에게 지급한다.
"""
documents.append(Document(
    page_content=rules_text, 
    metadata={"source": "학칙", "topic": "졸업/장학금"}
))
print("✅ 학사일정/학칙 임시 데이터 추가 완료!")

# 3. 벡터 DB (ChromaDB) 생성 및 데이터 저장 (인덱싱)
persist_directory = "./chroma_db"
print(f"⏳ 데이터를 벡터 DB에 임베딩 및 저장 중... (저장 경로: {persist_directory})")

# Chroma DB 인스턴스 생성 및 문서 추가
# 만약 이미 폴더가 있다면 기존 DB를 불러오고, 없으면 새로 만듭니다.
vectorstore = Chroma.from_documents(
    documents=documents,
    embedding=embeddings,
    persist_directory=persist_directory
)
print("✅ 벡터 DB 구축 완료!\n")

# 4. 테스트 (유사도 검색)
print("-" * 50)
print("🤖 챗봇(RAG) 검색 테스트를 시작합니다.")
print("-" * 50)

queries = [
    "이번 학기 기말고사는 언제야?",
    "성적 우수 장학금을 받으려면 학점이 몇 점 넘어야 해?",
    "최근 공지사항 중에 중요한 거 하나만 알려줘" # DB에 있는 실제 공지 기반으로 검색될 것입니다
]

for query in queries:
    print(f"\n[질문]: {query}")
    # k=2: 가장 비슷한 문서를 2개만 찾아옴
    results = vectorstore.similarity_search(query, k=2)
    
    for i, doc in enumerate(results):
        print(f"  -> [검색 결과 {i+1}] (출처: {doc.metadata.get('source')})")
        # 텍스트가 너무 길면 잘라서 출력
        preview = doc.page_content[:150].replace('\n', ' ') + "..."
        print(f"     내용: {preview}")
