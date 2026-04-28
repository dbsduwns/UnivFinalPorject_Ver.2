from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.timetable import (
    CustomScheduleCreate,
    CustomScheduleResponse,
    TimetableCourseCreate,
    TimetableCourseResponse,
    TimetableCreate,
    TimetableDetailResponse,
    TimetableResponse,
)
from app.services import timetable as timetable_service

router = APIRouter(prefix="/api/timetables", tags=["timetables"])


@router.post("/", response_model=TimetableResponse)
def create_timetable(
    data: TimetableCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return timetable_service.create_timetable(db, current_user, data)


@router.get("/", response_model=list[TimetableResponse])
def get_my_timetables(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return timetable_service.get_my_timetables(db, current_user)


@router.get("/{timetable_id}", response_model=TimetableDetailResponse)
def get_my_timetable(
    timetable_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    timetable = timetable_service.get_my_timetable_detail(db, current_user, timetable_id)
    if not timetable:
        raise HTTPException(status_code=404, detail="Timetable not found")
    return timetable


@router.post("/{timetable_id}/courses", response_model=TimetableCourseResponse)
def add_course_to_timetable(
    timetable_id: int,
    data: TimetableCourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return timetable_service.add_course_to_timetable(db, current_user, timetable_id, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{timetable_id}/courses/{course_id}")
def remove_course_from_timetable(
    timetable_id: int,
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        timetable_service.remove_course_from_timetable(db, current_user, timetable_id, course_id)
        return {"message": "Course removed from timetable"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{timetable_id}/custom-schedules", response_model=CustomScheduleResponse)
def create_custom_schedule(
    timetable_id: int,
    data: CustomScheduleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return timetable_service.create_custom_schedule(db, current_user, timetable_id, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{timetable_id}/custom-schedules", response_model=list[CustomScheduleResponse])
def get_custom_schedules(
    timetable_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return timetable_service.get_custom_schedules(db, current_user, timetable_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{timetable_id}/custom-schedules/{schedule_id}")
def delete_custom_schedule(
    timetable_id: int,
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        timetable_service.delete_custom_schedule(db, current_user, timetable_id, schedule_id)
        return {"message": "Custom schedule deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
