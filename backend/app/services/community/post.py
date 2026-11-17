import re, uuid
from datetime import datetime, timedelta
from typing import List
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.community.post import Post
from app.models.community.comment import Comment
from app.models.community.like import PostLike
from app.schemas.community.post import CreatePost, UpdatePost, PostResponse, HotPostResponse
from app.models.user import User
from app.core.storage import delete_community_image

def get_posts(
        db: Session,
        board_slug: str | None = None,
        keyword: str | None = None,    
        skip: int = 0,
        limit: int = 20,
        include_hidden: bool = False,
        current_user: User | None = None,
    ) -> List[PostResponse]:
    query = db.query(Post).options(selectinload(Post.author))
    if not include_hidden:
        query = query.filter(Post.is_hidden.is_(False))

    if board_slug:
        query = query.filter(Post.board_slug == board_slug)

    if keyword:
        search = f"%{keyword}%"
        query = query.filter(Post.title.ilike(search)|
                             Post.content.ilike(search)
        )

        
    posts = (
        query
        .order_by(Post.is_pinned.desc(), Post.created_at.desc(), Post.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return(
        [to_post_response(post, current_user) for post in posts]
    )


def get_hot_posts(
    db: Session,
    current_user: User | None = None,
    limit: int = 2,
) -> list[HotPostResponse]:
    """Return the top recent posts that meet the demo engagement threshold.

    Candidates are visible posts from the last seven days with at least two
    combined likes and non-hidden comments. The score favors likes slightly
    more than comments and decays as a post gets older.
    """
    now = datetime.utcnow()
    since = now - timedelta(days=7)
    like_counts = (
        db.query(
            PostLike.post_id.label("post_id"),
            func.count(PostLike.id).label("like_count"),
        )
        .group_by(PostLike.post_id)
        .subquery()
    )
    comment_counts = (
        db.query(
            Comment.post_id.label("post_id"),
            func.count(Comment.id).label("comment_count"),
        )
        .filter(Comment.is_hidden.is_(False))
        .group_by(Comment.post_id)
        .subquery()
    )

    candidates = (
        db.query(
            Post,
            func.coalesce(like_counts.c.like_count, 0).label("like_count"),
            func.coalesce(comment_counts.c.comment_count, 0).label("comment_count"),
        )
        .options(selectinload(Post.author))
        .outerjoin(like_counts, like_counts.c.post_id == Post.id)
        .outerjoin(comment_counts, comment_counts.c.post_id == Post.id)
        .filter(
            Post.is_hidden.is_(False),
            Post.created_at >= since,
        )
        .all()
    )

    ranked: list[tuple[float, Post, int, int]] = []
    for post, like_count, comment_count in candidates:
        like_count = int(like_count)
        comment_count = int(comment_count)
        if like_count + comment_count < 2:
            continue

        created_at = post.created_at
        if created_at.tzinfo is not None:
            created_at = created_at.replace(tzinfo=None)
        age_hours = max((now - created_at).total_seconds() / 3600, 0)
        engagement_score = like_count * 3 + comment_count * 2
        hot_score = engagement_score / ((age_hours + 2) ** 1.2)
        ranked.append((hot_score, post, like_count, comment_count))

    ranked.sort(key=lambda item: (-item[0], -item[1].created_at.timestamp(), -item[1].id))
    return [
        HotPostResponse(
            **to_post_response(post, current_user).model_dump(),
            like_count=like_count,
            comment_count=comment_count,
            hot_score=round(hot_score, 4),
        )
        for hot_score, post, like_count, comment_count in ranked[:limit]
    ]

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
        image_url=data.image_url,
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

    if not user.is_admin and (post.author_id != user.id or post.is_hidden):
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

    if not user.is_admin and post.author_id != user.id:
        raise PermissionError("You do not have permission to delete this post")

    image_path = post.image_path
    db.delete(post)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    delete_community_image(image_path)

def generate_post_slug(db: Session, title: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9가-힣]+", "-", title).strip("-")
    base = base or "post"

    while True:
        suffix = uuid.uuid4().hex[:8]
        slug = f"{base}-{suffix}"

        if not get_post_by_slug(db, slug):
            return slug

def to_post_response(post: Post, current_user: User | None = None) -> PostResponse:
    return PostResponse(
        id=post.id,
        slug=post.slug,
        board_slug=post.board_slug,
        title=post.title,
        content=post.content,
        image_url=post.image_url,
        author_name="익명" if post.is_anonymous else post.author.name,
        is_anonymous=post.is_anonymous,
        is_hidden=post.is_hidden,
        is_pinned=post.is_pinned,
        created_at=post.created_at,
        updated_at=post.updated_at,
        is_mine=current_user is not None and post.author_id == current_user.id,
    )
