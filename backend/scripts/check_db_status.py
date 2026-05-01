import sys
import os
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(backend_dir))

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

def main():
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

    sources = {}
    for metadata in data['metadatas']:
        source = metadata.get('source', 'Unknown')
        title = metadata.get('title', 'No Title')
        key = f"{source} - {title}"
        sources[key] = sources.get(key, 0) + 1

    for key, count in sorted(sources.items()):
        print(f"{key}: {count} documents")

if __name__ == "__main__":
    main()
