from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.community.like import PostLike, CommentLike
from app.models.user import User
from app.models.community.post import Post
from app.models.community.comment import Comment

def get_post_like_count(db: Session, post_id: int) -> int:

    validate_post_exists(db, post_id)
    
    return (
        db.query(PostLike)
        .filter(PostLike.post_id == post_id)
        .count()
    )

def is_post_liked(db: Session, user: User, post_id: int) -> bool:

    validate_post_exists(db, post_id)
    
    return (
        db.query(PostLike)
        .filter(
            PostLike.post_id == post_id,
            PostLike.user_id == user.id,
        )
        .first()
        is not None
    )

def toggle_post_like(db: Session, user: User, post_id: int) -> dict:
    
    validate_post_exists(db, post_id)

    like = (
        db.query(PostLike)
        .filter(
            PostLike.post_id == post_id,
            PostLike.user_id == user.id,
        )
        .first()
    )
    if like:
        db.delete(like)
        liked = False
    else:
        db.add(
            PostLike(
                post_id=post_id,
                user_id=user.id,
            )
        )
        liked=True

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise

    return {
        "liked": liked,
        "like_count": get_post_like_count(db, post_id),
    }

def get_comment_like_count(db: Session, comment_id: int) -> int:

    validate_comment_exists(db, comment_id)
    
    return (
        db.query(CommentLike)
        .filter(CommentLike.comment_id == comment_id)
        .count()
    )

def is_comment_liked(db: Session, user: User, comment_id: int) -> bool:
    
    validate_comment_exists(db, comment_id)
    
    return (
        db.query(CommentLike)
        .filter(
            CommentLike.comment_id == comment_id,
            CommentLike.user_id == user.id,
        )
        .first()
        is not None
    )

def toggle_comment_like(db: Session, user: User, comment_id: int) -> dict:

    validate_comment_exists(db, comment_id)

    comment = (
        db.query(Comment)
        .filter(Comment.id == comment_id)
        .first()
    )
    if comment.is_hidden:
        raise ValueError(
            "Comment is hidden. You do not have permission"
        )
    
    like = (
        db.query(CommentLike)
        .filter(
            CommentLike.comment_id == comment_id,
            CommentLike.user_id == user.id,
        )
        .first()
    )

    if like:
        db.delete(like)
        liked = False
    else:
        db.add(
            CommentLike(
                comment_id=comment_id,
                user_id=user.id,
            )
        )
        liked = True

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise

    return {
        "liked": liked,
        "like_count": get_comment_like_count(db, comment_id),
    }

def validate_post_exists(db: Session, post_id: int) -> Post:
    post = db.get(Post, post_id)

    if post is None:
        raise ValueError("Post not found")

    return post

def validate_comment_exists(db: Session, comment_id: int) -> Comment:
    comment = db.get(Comment, comment_id)

    if comment is None:
        raise ValueError("Comment not found")

    return comment
