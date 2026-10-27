from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.presence import UserPresenceResponse, UserPresenceUpdate
from app.services import presence as presence_service


router = APIRouter(prefix="/api/presence", tags=["presence"])


@router.put("", response_model=UserPresenceResponse)
def update_my_presence(
    data: UserPresenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """현재 로그인한 사용자의 앱 및 활성 대화방 상태를 갱신한다."""
    try:
        return presence_service.update_user_presence(db, current_user, data)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
