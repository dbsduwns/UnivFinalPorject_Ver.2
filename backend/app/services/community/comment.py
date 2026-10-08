from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.community.comment import Comment
from app.models.community.post import Post
from app.models.user import User
from app.schemas.community.comment import (
    CommentResponse,
    CreateComment,
    UpdateComment,
)


def get_comments(
    db: Session,
    post_id: int,
    parent_comment_id: int | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[CommentResponse]:
    """Return comments for a post, optionally limited to one reply level."""
    comments = (
        db.query(Comment)
        .options(selectinload(Comment.author))
        .filter(
            Comment.post_id == post_id,
            Comment.parent_comment_id == parent_comment_id,
        )
        .order_by(Comment.commented_at.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [to_comment_response(comment) for comment in comments]


def get_comment(
    db: Session,
    post_id: int,
    comment_id: int,
) -> Comment | None:
    """Find one comment that belongs to the given post."""
    return (
        db.query(Comment)
        .options(selectinload(Comment.author))
        .filter(
            Comment.id == comment_id,
            Comment.post_id == post_id,
        )
        .first()
    )


def create_comment(
    db: Session,
    user: User,
    post_id: int,
    data: CreateComment,
) -> Comment:
    """Create a top-level comment or a reply to an existing comment."""
    validate_post_exists(db, post_id)
    validate_parent_comment(db, post_id, data.parent_comment_id)

    comment = Comment(
        content=data.content,
        author_id=user.id,
        post_id=post_id,
        parent_comment_id=data.parent_comment_id,
        is_anonymous=data.is_anonymous,
    )

    try:
        db.add(comment)
        db.commit()
        db.refresh(comment)
    except IntegrityError:
        db.rollback()
        raise

    return comment


def update_comment(
    db: Session,
    user: User,
    post_id: int,
    comment_id: int,
    data: UpdateComment,
) -> Comment:
    comment = get_comment(db, post_id, comment_id)
    if comment is None:
        raise ValueError("Comment not found")

    if comment.author_id != user.id:
        raise PermissionError(
            "You do not have permission to update this comment"
        )

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(comment, key, value)

    try:
        db.commit()
        db.refresh(comment)
    except IntegrityError:
        db.rollback()
        raise

    return comment


def delete_comment(
    db: Session,
    user: User,
    post_id: int,
    comment_id: int,
) -> None:
    comment = get_comment(db, post_id, comment_id)
    if comment is None:
        raise ValueError("Comment not found")

    if comment.author_id != user.id:
        raise PermissionError(
            "You do not have permission to delete this comment"
        )

    db.delete(comment)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise


def validate_parent_comment(
    db: Session,
    post_id: int,
    parent_comment_id: int | None = None,
) -> Comment | None:
    if parent_comment_id is None:
        return None

    parent_comment = get_comment(db, post_id, parent_comment_id)
    if parent_comment is None:
        raise ValueError("Parent comment not found")

    return parent_comment

def validate_post_exists(db: Session, post_id: int) -> Post:
    post = db.get(Post, post_id)

    if post is None:
        raise ValueError("Post not found")

    return post

def to_comment_response(comment: Comment) -> CommentResponse:
    return CommentResponse(
        id=comment.id,
        content=comment.content,
        post_id=comment.post_id,
        author_name=(
            "익명" if comment.is_anonymous else comment.author.name
        ),
        parent_comment_id=comment.parent_comment_id,
        is_anonymous=comment.is_anonymous,
        commented_at=comment.commented_at,
        updated_at=comment.updated_at,
    )
