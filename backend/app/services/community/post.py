import re, uuid
from typing import List
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.community.post import Post
from app.schemas.community.post import CreatePost, UpdatePost, PostResponse
from app.models.user import User

def get_posts(
        db: Session,
        board_slug: str | None = None,
        keyword: str | None = None,    
        skip: int = 0,
        limit: int = 20,
    ) -> List[PostResponse]:
    query = db.query(Post).options(selectinload(Post.author))

    if board_slug:
        query = query.filter(Post.board_slug == board_slug)

    if keyword:
        search = f"%{keyword}%"
        query = query.filter(Post.title.ilike(search)|
                             Post.content.ilike(search)
        )

        
    posts = (
        query
        .order_by(Post.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return(
        [to_post_response(post) for post in posts]
    )

def get_post_by_slug(db: Session, post_slug: str):
    return (
        db.query(Post)
        .filter(Post.slug == post_slug)
        .first()
    )

def create_post(db: Session, user: User, board_slug: str, data: CreatePost) -> Post:
    post = Post(
        slug=generate_post_slug(db, data.title),
        board_slug=board_slug,
        title=data.title,
        content=data.content,
        author_id=user.id,
        is_anonymous=data.is_anonymous
    )
    try:
        db.add(post)
        db.commit()
        db.refresh(post)
    except IntegrityError:
        db.rollback()
        raise
    return post

def update_post(db: Session, user: User, post_slug: str, data: UpdatePost) -> Post:
    post = get_post_by_slug(db, post_slug)
    if not post:
        raise ValueError("Post not found")

    if post.author_id != user.id: 
        raise PermissionError("You do not have permission to update this post")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(post, key, value)
    try:
        db.commit()
        db.refresh(post)
    except IntegrityError:
        db.rollback()
        raise
    return post

def delete_post(db: Session, user: User, post_slug: str) -> None:
    post = get_post_by_slug(db, post_slug)
    if not post:
        raise ValueError("Post not found")

    if post.author_id != user.id:
        raise PermissionError("You do not have permission to delete this post")

    db.delete(post)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise

def generate_post_slug(db: Session, title: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9가-힣]+", "-", title).strip("-")
    base = base or "post"

    while True:
        suffix = uuid.uuid4().hex[:8]
        slug = f"{base}-{suffix}"

        if not get_post_by_slug(db, slug):
            return slug

def to_post_response(post: Post) -> PostResponse:
    return PostResponse(
        id=post.id,
        slug=post.slug,
        board_slug=post.board_slug,
        title=post.title,
        content=post.content,
        author_name="익명" if post.is_anonymous else post.author.name,
        is_anonymous=post.is_anonymous,
        created_at=post.created_at,
        updated_at=post.updated_at,
    )