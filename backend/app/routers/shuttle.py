from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_admin_user
from app.database import get_db
from app.schemas.shuttle import ShuttleCrawlResponse, ShuttleResponse
from app.services import shuttle as shuttle_service

router = APIRouter(prefix="/api/shuttles", tags=["shuttle"])


@router.get("/", response_model=list[ShuttleResponse])
def get_shuttle_schedules(
    semester: str | None = None,
    db: Session = Depends(get_db),
):
    return shuttle_service.get_shuttle_schedules(db, semester=semester)


@router.get("/latest", response_model=ShuttleResponse)
def get_latest_shuttle_schedule(db: Session = Depends(get_db)):
    shuttle_schedule = shuttle_service.get_latest_shuttle_schedule(db)
    if not shuttle_schedule:
        raise HTTPException(status_code=404, detail="Shuttle schedule not found")
    return shuttle_schedule


@router.post(
    "/crawl",
    response_model=ShuttleCrawlResponse,
    dependencies=[Depends(get_current_admin_user)],
)
def crawl_shuttle_schedules(db: Session = Depends(get_db)):
    try:
        shuttle_schedule = shuttle_service.crawl_and_save_shuttle_schedule(db)
        return {
            "message": "Shuttle schedule crawling completed",
            "item": shuttle_schedule,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
