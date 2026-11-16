from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_current_admin_user
from app.schemas.community.post import AdminPostUpdate
from app.database import get_db
from app.models.user import User
from app.services.community import post as post_service
from app.schemas.community import (
    CreatePost,
    UpdatePost,
    PostResponse,
)
from app.core.storage import delete_community_image, upload_community_image

router = APIRouter(prefix="/api/community", tags=["community"])
admin_router = APIRouter(prefix="/api/admin/community/posts", tags=["admin"])


@admin_router.get("", response_model=list[PostResponse])
def get_admin_posts(
    board_slug: str | None = None,
    keyword: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    return post_service.get_posts(db, board_slug, keyword, skip, limit, include_hidden=True, current_user=admin)


@admin_router.get("/{post_slug}", response_model=PostResponse)
def get_admin_post(
    post_slug: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    post = post_service.get_post_by_slug(db, post_slug)
    if post is None:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다")
    return post_service.to_post_response(post, admin)


@admin_router.patch("/{post_slug}", response_model=PostResponse)
def manage_post(
    post_slug: str,
    data: AdminPostUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    post = post_service.get_post_by_slug(db, post_slug)
    if post is None:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다")
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(post, field, value)
    db.commit()
    db.refresh(post)
    return post_service.to_post_response(post)

@router.get("/", response_model=list[PostResponse])
def get_posts(
    db: Session = Depends(get_db),
    board_slug: str | None = None,
    keyword: str | None = None,
    skip: int = 0,
    limit: int = 20,
    user: User = Depends(get_current_user),
):
    return post_service.get_posts(db, board_slug, keyword, skip, limit, current_user=user)

@router.get("/slug", response_model=PostResponse)
def get_post_by_slug(
    post_slug: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    post = post_service.get_post_by_slug(db, post_slug)
    if not post or post.is_hidden:
        raise HTTPException(status_code=404, detail="Post not found")
    return post_service.to_post_response(post, user)

@router.post("/posts", response_model=PostResponse)
def create_post(
    board_slug: str,
    title: str = Form(...),
    content: str = Form(...),
    is_anonymous: bool = Form(False),
    image: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    uploaded_image_path = None
    try:
        image_url = None
        image_path = None
        if image is not None:
            image_url, image_path = upload_community_image(image, user.id)
            uploaded_image_path = image_path
        data = CreatePost(
            title=title,
            content=content,
            is_anonymous=is_anonymous,
            image_url=image_url,
        )
        post = post_service.create_post(db, user, board_slug, data)
        post.image_path = image_path
        db.commit()
        db.refresh(post)
        return post_service.to_post_response(post, user)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        delete_community_image(uploaded_image_path)
        raise

@router.put("/{post_slug}", response_model=PostResponse)
def update_post(
    post_slug: str,
    data: UpdatePost,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        post = post_service.update_post(db, user, post_slug, data)
        return post_service.to_post_response(post, user)
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
