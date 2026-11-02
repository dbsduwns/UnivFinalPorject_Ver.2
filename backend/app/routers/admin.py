from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_admin_user
from app.database import get_db
from app.models.user import User
from app.schemas.admin import AdminDashboardResponse, AdminRoleResponse, AdminRoleUpdate, AdminUserActiveUpdate, AdminUserBlockResponse, AdminUserResponse
from app.models.community.user_block import UserBlock
from app.services import admin as admin_service


router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/dashboard", response_model=AdminDashboardResponse)
def get_dashboard(db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin_user)):
    return admin_service.get_dashboard(db)


@router.get("/users", response_model=list[AdminUserResponse])
def get_users(
    keyword: str | None = Query(None, max_length=100),
    is_active: bool | None = None,
    is_admin: bool | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    query = db.query(User)
    if keyword and keyword.strip():
        term = f"%{keyword.strip()}%"
        query = query.filter(User.email.ilike(term) | User.name.ilike(term) | User.student_id.ilike(term))
    if is_active is not None:
        query = query.filter(User.is_active.is_(is_active))
    if is_admin is not None:
        query = query.filter(User.is_admin.is_(is_admin))
    return query.order_by(User.created_at.desc(), User.id.desc()).offset(skip).limit(limit).all()


@router.get("/users/{user_id}", response_model=AdminUserResponse)
def get_user(user_id: int, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin_user)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다")
    return user


@router.patch("/users/{user_id}/active", response_model=AdminUserResponse)
def update_user_active(user_id: int, data: AdminUserActiveUpdate, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin_user)):
    try:
        return admin_service.update_user_active_status(db, current_admin, user_id, data.is_active)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    try:
        admin_service.delete_user_account(db, current_admin, user_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


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
