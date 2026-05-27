from app.models.notice import Notice

def get_notices(db, category=None, keyword=None):
    query = db.query(Notice)
    if category:
        query = query.filter(Notice.category == category)
    if keyword:
        query = query.filter(Notice.title.contains(keyword))
    
    # 최신 공지가 먼저 오도록 정렬 (작성일 기준, 없으면 ID 기준)
    return query.order_by(Notice.published_at.desc(), Notice.id.desc()).all()

def get_notice(db, notice_id: int):
    return db.query(Notice).filter(Notice.id == notice_id).first()
   
def update_notice(db, notice_id: int, data):
    notice = get_notice(db, notice_id)
    if not notice:
        raise ValueError("공지사항을 찾을 수 없습니다")
    if data.title: notice.title = data.title
    if data.content: notice.content = data.content
    if data.category: notice.category = data.category
    db.commit()
    db.refresh(notice)
    return notice

def delete_notice(db, notice_id: int):
    notice = get_notice(db, notice_id)
    if not notice:
         raise ValueError("공지사항을 찾을 수 없습니다")
    db.delete(notice)
    db.commit()
	

