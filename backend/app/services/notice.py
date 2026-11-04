from app.models.notice import Notice
from app.models.notice_read import NoticeRead
from datetime import datetime, timezone
from app.core.ai_bot import campus_ai_bot

def get_notices(db, category=None, keyword=None):
    query = db.query(Notice)
    if category:
        query = query.filter(Notice.category == category)
    if keyword and keyword.strip():
        query = query.filter(Notice.title.contains(keyword.strip(), autoescape=True))
    
    # 고정 공지를 먼저 표시하고, 같은 고정 상태에서는 최신순으로 정렬한다.
    return query.order_by(Notice.is_important.desc(), Notice.published_at.desc(), Notice.id.desc()).all()

def get_notice(db, notice_id: int):
    return db.query(Notice).filter(Notice.id == notice_id).first()
   
def update_notice(db, notice_id: int, data):
    notice = get_notice(db, notice_id)
    if not notice:
        raise ValueError("공지사항을 찾을 수 없습니다")
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(notice, field, value)
    db.commit()
    db.refresh(notice)
    return notice

def delete_notice(db, notice_id: int):
    notice = get_notice(db, notice_id)
    if not notice:
         raise ValueError("공지사항을 찾을 수 없습니다")

    # DB를 먼저 삭제하면 RAG 삭제 실패 시 고아 벡터 문서가 남을 수 있으므로
    # RAG 정리 성공 후 DB 삭제를 진행한다.
    rag_deleted = 0
    if notice.source_key:
        rag_deleted = campus_ai_bot.delete_documents_by_metadata(
            {"source_key": notice.source_key}
        )
    # 마이그레이션 이전 RAG 문서에는 source_key가 없을 수 있으므로
    # 제목 기준의 레거시 문서도 함께 정리한다.
    rag_deleted += campus_ai_bot.delete_documents_by_metadata(
        {"source": "공지사항", "title": notice.title}
    )

    # 공지에 종속된 읽음 기록도 함께 제거해 DB에 고아 행을 남기지 않는다.
    db.query(NoticeRead).filter(NoticeRead.notice_id == notice.id).delete(
        synchronize_session=False,
    )
    db.delete(notice)
    db.commit()

    return {"rag_deleted": rag_deleted}
	

def create_notice(db, data):
    notice = Notice(**data.model_dump(), published_at=datetime.now(timezone.utc))
    db.add(notice)
    db.commit()
    db.refresh(notice)
    return notice

