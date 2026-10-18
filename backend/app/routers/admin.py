from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_admin_user
from app.database import get_db
from app.models.user import User
from app.schemas.admin import AdminRoleResponse, AdminRoleUpdate, AdminUserBlockResponse
from app.models.community.user_block import UserBlock
from app.services import admin as admin_service


router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/user-blocks", response_model=list[AdminUserBlockResponse])
def get_all_user_blocks(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    return db.query(UserBlock).order_by(UserBlock.created_at.desc(), UserBlock.id.desc()).offset(skip).limit(limit).all()


@router.patch(
    "/users/{user_id}/role",
    response_model=AdminRoleResponse,
)
def update_user_admin_role(
    user_id: int,
    data: AdminRoleUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    try:
        return admin_service.update_admin_role(
            db,
            current_admin,
            user_id,
            data.is_admin,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
