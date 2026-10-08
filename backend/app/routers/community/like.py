from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.community import like as like_service

router = APIRouter(prefix="/api/community", tags=["community"])

@router.get("/posts/{post_id}/likes", response_model=int)
def get_post_like(post_id: int, db: Session = Depends(get_db)):
    try:
        like = like_service.get_post_like_count(db, post_id)
        return like
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/posts/{post_id}/likes/me", response_model=bool)
def is_post_liked(
    post_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    try:
        is_post_liked = like_service.is_post_liked(db, user, post_id)
        return is_post_liked
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/posts/{post_id}/likes", response_model=dict)
def toggle_post_like(
    post_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    try:
        toggle_post_like = like_service.toggle_post_like(db, user, post_id)
        return toggle_post_like
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/posts/{post_id}/comments/{comment_id}/likes", response_model=int)
def get_comment_like(comment_id: int, db: Session = Depends(get_db)):
    try:
        like = like_service.get_comment_like_count(db, comment_id)
        return like
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/posts/{post_id}/comments/{comment_id}/likes/me", response_model=bool)
def is_comment_liked(
    comment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    try:
        is_comment_liked = like_service.is_comment_liked(db, user, comment_id)
        return is_comment_liked
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/posts/{post_id}/comments/{comment_id}/likes", response_model=dict)
def toggle_comment_like(
    comment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    try:
        toggle_comment_like = like_service.toggle_comment_like(db, user, comment_id)
        return toggle_comment_like
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
