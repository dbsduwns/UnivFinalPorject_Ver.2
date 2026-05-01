from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.core.dependencies import get_current_admin_user
from app.schemas.daily_menu import DailyMenuResponse
from app.services import daily_menu as daily_menu_services

router = APIRouter(prefix="/api/daily-menus", tags=["daily-menus"])

@router.get("/", response_model=list[DailyMenuResponse])
def get_daily_menu(date: str, db: Session = Depends(get_db)):
    try:
        daily_menu = daily_menu_services.get_daily_menu(db, date)
        return daily_menu
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/crawl")
def crawl_daily_menu(
    max_items: int | None = None,
    current_admin: User = Depends(get_current_admin_user), # 관리자 검증
):
    try:
        menus = daily_menu_services.crawl_and_save(max_items=max_items)
        return {"message": "Daily menu crawling completed", "count": len(menus), "items": menus}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
