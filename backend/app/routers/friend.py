from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.friend import (
    FriendUserResponse,
    FriendRequestsSummary,
    FriendSearchItem,
    FriendRequestCreate,
    FriendTimetableResponse,
)
from app.schemas.timetable import TimetableResponse
from app.services import friend as friend_service

router = APIRouter(prefix="/api/friends", tags=["friends"])

@router.get("/search", response_model=List[FriendSearchItem])
def search_friends(
    query: str = Query(..., min_length=1, description="학번, 이름, 이메일 검색어"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """학번, 이름, 이메일로 사용자를 검색하고 현재 친구 관계 상태를 반환합니다."""
    return friend_service.search_users(db, current_user, query)

@router.post("/requests")
def send_friend_request(
    data: FriendRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """친구 요청을 보냅니다 (addressee_id 또는 student_id)."""
    try:
        req = friend_service.send_friend_request(
            db,
            current_user,
            addressee_id=data.addressee_id,
            student_id=data.student_id,
        )
        return {"message": "친구 요청이 전송되었습니다.", "request_id": req.id, "status": req.status}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/requests", response_model=FriendRequestsSummary)
def get_friend_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """받은 친구 요청 및 보낸 친구 요청 목록을 조회합니다."""
    return friend_service.get_friend_requests(db, current_user)

@router.post("/requests/{request_id}/accept")
def accept_friend_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """받은 친구 요청을 수락합니다."""
    try:
        req = friend_service.accept_friend_request(db, current_user, request_id)
        return {"message": "친구 요청을 수락했습니다.", "request_id": req.id, "status": req.status}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/requests/{request_id}/reject")
def reject_friend_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """받은 친구 요청을 거절합니다."""
    try:
        friend_service.reject_friend_request(db, current_user, request_id)
        return {"message": "친구 요청을 거절했습니다."}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/requests/{request_id}")
def cancel_friend_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """보낸 친구 요청을 취소합니다."""
    try:
        friend_service.cancel_friend_request(db, current_user, request_id)
        return {"message": "보낸 친구 요청을 취소했습니다."}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/", response_model=List[FriendUserResponse])
def get_friends(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """수락 완료된 내 친구 목록을 조회합니다."""
    return friend_service.get_friends(db, current_user)

@router.delete("/{friend_id}")
def delete_friend(
    friend_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """친구 관계를 해제(삭제)합니다."""
    try:
        friend_service.delete_friend(db, current_user, friend_id)
        return {"message": "친구 관계가 해제되었습니다."}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/{friend_id}/timetables", response_model=List[TimetableResponse])
def get_friend_timetables(
    friend_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """친구의 시간표 목록을 조회합니다 (친구 관계 검증 필수)."""
    try:
        return friend_service.get_friend_timetables(db, current_user, friend_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

@router.get("/{friend_id}/timetable", response_model=FriendTimetableResponse)
def get_friend_timetable_detail(
    friend_id: int,
    timetable_id: Optional[int] = Query(None, description="특정 시간표 ID (생략 시 대표 시간표)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """친구의 시간표 상세 정보(강의 및 일정 포함)를 조회합니다 (친구 관계 검증 필수)."""
    try:
        return friend_service.get_friend_timetable_detail(
            db, current_user, friend_id, timetable_id=timetable_id
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
