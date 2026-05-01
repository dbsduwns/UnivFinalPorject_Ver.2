import os
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(backend_dir))

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

def check_raw_data():
    embeddings = HuggingFaceEmbeddings(
        model_name="jhgan/ko-sroberta-multitask",
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )
    persist_directory = str(backend_dir / "chroma_db")
    
    if not os.path.exists(persist_directory):
        print(f"Error: {persist_directory} not found")
        return

    vectorstore = Chroma(persist_directory=persist_directory, embedding_function=embeddings)
    data = vectorstore.get()
    
    print(f"Total documents: {len(data['ids'])}")
    
    # 5개 샘플 출력
    for i in range(min(5, len(data['ids']))):
        content = data['documents'][i]
        metadata = data['metadatas'][i]
        print(f"--- Sample {i+1} ---")
        print(f"Metadata: {metadata}")
        # repr()을 사용하면 깨진 문자인지 제어 문자인지 정확히 알 수 있습니다.
        print(f"Content (repr): {repr(content[:200])}")
        print(f"Content (plain): {content[:200]}")
        print("-" * 20)

if __name__ == "__main__":
    check_raw_data()
