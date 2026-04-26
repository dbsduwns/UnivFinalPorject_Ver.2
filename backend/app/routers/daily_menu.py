from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.daily_menu import DailyMenuResponse
from app.services import daily_menu as daily_menu_services

router = APIRouter(prefix="/api/daily-menus", tags=["daily-menus"])

@router.get("/")
def get_daily_menu(date: str, db: Session = Depends(get_db)):
    try:
        daily_menu = daily_menu_services.get_daily_menu(db, date)
        return daily_menu
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
