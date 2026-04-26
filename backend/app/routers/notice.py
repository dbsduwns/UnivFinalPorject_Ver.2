from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.notice import NoticeResponse, NoticeUpdate
from app.services import notice as notice_service

router = APIRouter(prefix="/api/notices", tags=["notices"])

@router.get("/")
def get_notices(category: str = None, keyword: str = None, db: Session = Depends(get_db)):
	try:
		notice = notice_service.get_notices(db, category, keyword)
		return notice
	except ValueError as e:
		raise HTTPException(status_code=400, detail=str(e))

@router.get("/{notice_id}")
def get_notice(notice_id: int, db: Session = Depends(get_db)):
	try:
		notice = notice_service.get_notice(db, notice_id)
		return notice
	except ValueError as e:
		raise HTTPException(status_code=400, detail=str(e))

@router.put("/{notice_id}")
def update_notice(notice_id: int, data: NoticeUpdate, db: Session = Depends(get_db)):
	try:
		notice = notice_service.update_notice(db, notice_id, data)
		return notice
	except ValueError as e:
		raise HTTPException(status_code=404, detail=str(e))

@router.delete("/{notice_id}")
def delete_notice(notice_id: int, db: Session = Depends(get_db)):
	try:
		notice = notice_service.delete_notice(db, notice_id)
		return {"message": "삭제되었습니다"}	
	except ValueError as e:
		raise HTTPException(status_code=404, detail=str(e))