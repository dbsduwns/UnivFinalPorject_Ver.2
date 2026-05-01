import os
import sys
from pathlib import Path

# backend 폴더를 path에 추가
backend_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(backend_dir))

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

def export_contents():
    print("⏳ 벡터 DB 연결 중...")
    embeddings = HuggingFaceEmbeddings(
        model_name="jhgan/ko-sroberta-multitask",
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )
    persist_directory = str(backend_dir / "chroma_db")
    
    if not os.path.exists(persist_directory):
        print(f"❌ 에러: {persist_directory} 폴더를 찾을 수 없습니다.")
        return

    vectorstore = Chroma(persist_directory=persist_directory, embedding_function=embeddings)
    
    # 모든 데이터 가져오기 (ids, documents, metadatas)
    data = vectorstore.get()
    
    output_file = backend_dir / "db_contents_export.txt"
    
    print(f"📄 총 {len(data['ids'])}개의 문서를 추출하여 파일로 저장합니다...")
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"=== ChromaDB Export (Total: {len(data['ids'])} documents) ===\n\n")
        
        # 문서 순회 (가독성을 위해 메타데이터와 본문 함께 출력)
        for i in range(len(data['ids'])):
            doc_id = data['ids'][i]
            metadata = data['metadatas'][i]
            content = data['documents'][i]
            
            source = metadata.get('source', 'N/A')
            title = metadata.get('title', 'N/A')
            clause = metadata.get('clause', 'N/A')
            
            f.write(f"[{i+1}] ID: {doc_id}\n")
            f.write(f"    출처: {source}\n")
            f.write(f"    제목: {title}\n")
            f.write(f"    조항: {clause}\n")
            f.write(f"    내용 요약: {content[:100].replace('\\n', ' ')}...\n")
            f.write("-" * 80 + "\n")
            f.write(f"{content}\n")
            f.write("=" * 80 + "\n\n")

    print(f"✅ 추출 완료! 아래 경로에서 확인하세요:\n{output_file}")

if __name__ == "__main__":
    export_contents()
