from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.user_notification import UserNotification
from app.schemas.notification import (
    NotificationCenterResponse,
    NotificationReadAllResponse,
    NotificationResponse,
    NotificationUnreadCountResponse,
)


router = APIRouter(prefix="/api/notifications", tags=["notifications"])


def _unread_count(db: Session, user_id: int) -> int:
    return (
        db.query(UserNotification)
        .filter(
            UserNotification.user_id == user_id,
            UserNotification.read_at.is_(None),
        )
        .count()
    )


@router.get("", response_model=NotificationCenterResponse)
def get_notifications(
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = (
        db.query(UserNotification)
        .filter(UserNotification.user_id == current_user.id)
        .order_by(UserNotification.created_at.desc(), UserNotification.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return NotificationCenterResponse(
        items=items,
        unread_count=_unread_count(db, current_user.id),
    )


@router.get("/unread-count", response_model=NotificationUnreadCountResponse)
def get_unread_notification_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return {"unread_count": _unread_count(db, current_user.id)}


@router.post("/read-all", response_model=NotificationReadAllResponse)
def read_all_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    read_at = datetime.now(timezone.utc)
    updated_count = (
        db.query(UserNotification)
        .filter(
            UserNotification.user_id == current_user.id,
            UserNotification.read_at.is_(None),
        )
        .update({UserNotification.read_at: read_at}, synchronize_session=False)
    )
    db.commit()
    return {"updated_count": updated_count}


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
def read_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notification = (
        db.query(UserNotification)
        .filter(
            UserNotification.id == notification_id,
            UserNotification.user_id == current_user.id,
        )
        .first()
    )
    if notification is None:
        raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다.")
    if notification.read_at is None:
        notification.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(notification)
    return notification
