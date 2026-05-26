import os
import sys
from pathlib import Path
import shutil

# backend 폴더를 path에 추가
backend_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(backend_dir))

from app.database import SessionLocal, engin
from app.models.notice import Notice
from app.core.ai_bot import campus_ai_bot

def reset_notices():
    """
    공지사항 관련 데이터를 초기화합니다.
    1. SQL DB의 notices 테이블 삭제
    2. ChromaDB의 벡터 데이터 삭제
    """
    print("🗑️ [초기화] 공지사항 데이터 초기화를 시작합니다...")

    # 1. SQL 데이터 삭제
    db = SessionLocal()
    try:
        print("📝 SQL DB에서 모든 공지사항을 삭제 중...")
        num_deleted = db.query(Notice).delete()
        db.commit()
        print(f"✅ SQL DB 삭제 완료: {num_deleted}개의 공지사항 삭제됨")
    except Exception as e:
        print(f"❌ SQL DB 삭제 중 오류 발생: {e}")
        db.rollback()
    finally:
        db.close()

    # 2. ChromaDB 데이터 삭제
    # ChromaDB는 폴더 자체를 삭제하는 것이 가장 확실한 초기화 방법입니다.
    chroma_dir = backend_dir / "chroma_db"
    if chroma_dir.exists():
        print(f"📂 벡터 DB(Chroma) 초기화 중: {chroma_dir}")
        try:
            # 안전을 위해 폴더를 삭제하고 다시 생성될 수 있게 함
            shutil.rmtree(chroma_dir)
            print("✅ 벡터 DB 폴더 삭제 완료")
        except Exception as e:
            print(f"❌ 벡터 DB 삭제 중 오류 발생: {e}")
    else:
        print("ℹ️ 삭제할 벡터 DB 폴더가 없습니다.")

    print("\n✨ 초기화가 완료되었습니다. 이제 V3 크롤러를 실행할 수 있습니다.")

if __name__ == "__main__":
    confirm = input("❗ 정말 모든 공지사항 데이터를 초기화하시겠습니까? (y/n): ")
    if confirm.lower() == 'y':
        reset_notices()
    else:
        print("❌ 작업을 취소합니다.")
