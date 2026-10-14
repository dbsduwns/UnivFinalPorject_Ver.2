from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.commute import (
    CommuteProfileCreate,
    CommuteAddressSearchResult,
    CommuteProfileResponse,
    CommuteProfileUpdate,
    CommuteSettingsUpdate,
    CommuteTodayResponse,
)
from app.services import commute as commute_service


router = APIRouter(prefix="/api/commute", tags=["commute"])


@router.get("/addresses", response_model=list[CommuteAddressSearchResult])
def search_commute_addresses(
    q: str = Query(min_length=2, max_length=100),
    current_user: User = Depends(get_current_user),
):
    del current_user
    try:
        return commute_service.search_addresses(q)
    except commute_service.GeocodingError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/profile", response_model=CommuteProfileResponse)
def get_commute_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = commute_service.get_commute_profile(db, current_user)
    if profile is None:
        raise HTTPException(status_code=404, detail="Commute profile not found")
    return profile


@router.post(
    "/profile",
    response_model=CommuteProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_commute_profile(
    data: CommuteProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return commute_service.create_commute_profile(db, current_user, data)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail="Commute profile already exists",
        ) from exc
    except commute_service.GeocodingError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.patch("/profile", response_model=CommuteProfileResponse)
def update_commute_profile(
    data: CommuteProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return commute_service.update_commute_profile(db, current_user, data)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except commute_service.GeocodingError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.delete("/profile", status_code=status.HTTP_204_NO_CONTENT)
def delete_commute_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        commute_service.delete_commute_profile(db, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/settings", response_model=CommuteProfileResponse)
def update_commute_settings(
    data: CommuteSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return commute_service.update_commute_setting(db, current_user, data)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/today", response_model=CommuteTodayResponse)
def get_today_commute(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return commute_service.get_today_commute(db, current_user)
