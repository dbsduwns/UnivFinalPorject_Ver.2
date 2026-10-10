from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_current_admin_user
from app.database import get_db
from app.models.user import User
from app.services.community import comment as comment_service
from app.schemas.community.comment import ModerateComment
from app.schemas.community import (
    CreateComment,
    UpdateComment,
    CommentResponse,
)

router = APIRouter(prefix="/api/community", tags=["community"])
admin_router = APIRouter(prefix="/api/admin/community", tags=["admin"])

@router.get("/comments", response_model=list[CommentResponse])
def get_comments(
    post_id: int,
    parent_comment_id: int | None = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return comment_service.get_comments(
            db,
            current_user,
            post_id,
            parent_comment_id,
            skip,
            limit,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/comments/{post_id}/{comment_id}", response_model=CommentResponse)
def get_comment(
    post_id: int,
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    comment = comment_service.get_comment(db, post_id, comment_id)

    if comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    return comment_service.to_comment_response(comment, current_user)


@router.post("/comments", response_model=CommentResponse)
def create_comment(
    post_id: int,
    data: CreateComment,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        comment = comment_service.create_comment(db, user, post_id, data)
        return comment_service.to_comment_response(comment, user)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.put("/comments/{post_id}/{comment_id}", response_model=CommentResponse)
def update_comment(
    post_id: int,
    comment_id: int,
    data: UpdateComment,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        comment = comment_service.update_comment(db, user, post_id, comment_id, data)
        return comment_service.to_comment_response(comment, user)
    
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

@admin_router.patch(
    "/comments/{post_id}/{comment_id}/moderation",
    response_model=CommentResponse,
)
def moderate_comment(
    post_id: int,
    comment_id: int,
    data: ModerateComment,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    try:
        moderated_comment = comment_service.moderate_comment(db, current_admin, post_id, comment_id, data)
        return comment_service.to_comment_response(moderated_comment, current_admin)
    
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

@router.delete("/comments/{post_id}/{comment_id}")
def delete_comment(
    post_id: int,
    comment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        comment = comment_service.delete_comment(db, user, post_id, comment_id)
        return {"message": "삭제되었습니다"}
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
