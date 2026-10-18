from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.notice import NoticeResponse, NoticeUpdate, NoticeCreate
from app.services import notice as notice_service
from app.models.user import User
from app.core.dependencies import get_current_admin_user

router = APIRouter(prefix="/api/notices", tags=["notices"])


@router.post("/", response_model=NoticeResponse, status_code=201)
def create_notice(
    data: NoticeCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    return notice_service.create_notice(db, data)

@router.get("/", response_model=list[NoticeResponse])
def get_notices(category: str = None, keyword: str = None, db: Session = Depends(get_db)):
	try:
		notice = notice_service.get_notices(db, category, keyword)
		return notice
	except ValueError as e:
		raise HTTPException(status_code=400, detail=str(e))

@router.get("/{notice_id}", response_model=NoticeResponse)
def get_notice(notice_id: int, db: Session = Depends(get_db)):
	try:
		notice = notice_service.get_notice(db, notice_id)
		if not notice:
			raise HTTPException(status_code=404, detail="Notice not found")
		return notice
	except ValueError as e:
		raise HTTPException(status_code=400, detail=str(e))

@router.post("/crawl")
def crawl_notices(
		max_items: int | None = None,
		current_admin: User = Depends(get_current_admin_user), # 관리자 검증
	):
	try:
		# Playwright는 크롤링 요청이 실제로 들어올 때만 로드한다.
		from app.crawlers.notice_crawler import crawl_notice_list, save_notices

		notices = crawl_notice_list(max_items=max_items)
		save_notices(notices)
		return {"message": "Notice crawling completed", "count": len(notices)}
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))

@router.put("/{notice_id}", response_model=NoticeResponse)
def update_notice(
		notice_id: int,
		data: NoticeUpdate,
		db: Session = Depends(get_db),
		current_admin: User = Depends(get_current_admin_user), # 관리자 검증
	):
	try:
		notice = notice_service.update_notice(db, notice_id, data)
		return notice
	except ValueError as e:
		raise HTTPException(status_code=404, detail=str(e))

@router.delete("/{notice_id}")
def delete_notice(
		notice_id: int,
		db: Session = Depends(get_db),
		current_admin: User = Depends(get_current_admin_user), # 관리자 검증
	):
	try:
		notice = notice_service.delete_notice(db, notice_id)
		return {"message": "삭제되었습니다"}	
	except ValueError as e:
		raise HTTPException(status_code=404, detail=str(e))
