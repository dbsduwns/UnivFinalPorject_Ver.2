from app.models.notice import Notice
from datetime import datetime, timezone

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
    db.delete(notice)
    db.commit()
	

def create_notice(db, data):
    notice = Notice(**data.model_dump(), published_at=datetime.now(timezone.utc))
    db.add(notice)
    db.commit()
    db.refresh(notice)
    return notice

