from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.community import UserBlockResponse
from app.services.community import user_block as user_block_service


router = APIRouter(prefix="/api/community", tags=["community"])


@router.get("/userblocks", response_model=list[UserBlockResponse])
def get_user_blocks(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return user_block_service.get_user_blocks(db, current_user, skip, limit)


@router.post(
    "/userblocks",
    response_model=UserBlockResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_user_block(
    comment_id: int | None = Query(default=None, gt=0),
    post_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return user_block_service.create_user_block(db, current_user, comment_id, post_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.delete("/userblocks/{block_id}")
def delete_user_block(
    block_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        user_block_service.delete_user_block(db, current_user, block_id)
        return {"message": "차단이 해제되었습니다"}
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
