from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.community import post as post_service
from app.schemas.community import (
    CreatePost,
    UpdatePost,
    PostResponse,
)

router = APIRouter(prefix="/api/community", tags=["community"])

@router.get("/", response_model=list[PostResponse])
def get_posts(
    db: Session = Depends(get_db),
    board_slug: str | None = None,
    keyword: str | None = None,
    skip: int = 0,
    limit: int = 20,
):
    return post_service.get_posts(db, board_slug,  keyword, skip, limit)

@router.get("/slug", response_model=PostResponse)
def get_post_by_slug(post_slug: str, db: Session = Depends(get_db)):
    post = post_service.get_post_by_slug(db, post_slug)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post_service.to_post_response(post)

@router.post("/posts", response_model=PostResponse)
def create_post(
    board_slug: str,
    data: CreatePost,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        post = post_service.create_post(db, user, board_slug, data)
        return post_service.to_post_response(post)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.put("/{post_slug}", response_model=PostResponse)
def update_post(
    post_slug: str,
    data: UpdatePost,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        post = post_service.update_post(db, user, post_slug, data)
        return post_service.to_post_response(post)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

@router.delete("/{post_slug}")
def delete_post(
    post_slug: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        post=post_service.delete_post(db, user, post_slug)
        return {"message": "삭제되었습니다"}
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))