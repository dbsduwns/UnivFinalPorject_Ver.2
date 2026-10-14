from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.community.comment import Comment
from app.models.community.post import Post
from app.models.community.user_block import UserBlock
from app.models.user import User
from app.schemas.community.comment import (
    CommentResponse,
    CreateComment,
    UpdateComment,
    ModerateComment,
)


def get_comments(
    db: Session,
    user: User,
    post_id: int,
    parent_comment_id: int | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[CommentResponse]:
    """Return comments for a post, optionally limited to one reply level."""
    blocked_user_ids = (
        db.query(UserBlock.blocked_user_id)
        .filter(UserBlock.blocker_id == user.id)
        .scalar_subquery()
    )

    comments = (
        db.query(Comment)
        .options(selectinload(Comment.author))
        .filter(
            Comment.post_id == post_id,
            Comment.parent_comment_id == parent_comment_id,
            ~Comment.author_id.in_(blocked_user_ids),
        )
        .order_by(Comment.commented_at.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [to_comment_response(comment, user) for comment in comments]


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
    if comment.is_hidden:
        raise PermissionError(
            "Comment is Hidden, You do not have permission to update this"
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
    if comment.is_hidden:
        raise PermissionError(
            "Comment is Hidden, You do not have permission to update this"
        )

    db.delete(comment)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise

def moderate_comment(
    db: Session,
    admin: User,
    post_id: int,
    comment_id: int,
    data: ModerateComment,
) -> Comment:
    
    comment = (
        db.query(Comment)
        .filter(
            Comment.post_id == post_id,
            Comment.id == comment_id,
        )
        .first()
    )
    if comment is None:
        raise ValueError("Comment not found")
    if admin.is_admin is False:
        raise PermissionError("You do not have permission to access")

    if data.action == 'hide':
        comment.is_hidden = True
        comment.hidden_by_id = admin.id
        comment.hidden_at = func.now()
        comment.hidden_reason = data.reason
    if data.action == 'restore':
        comment.is_hidden = False
        comment.hidden_by_id = None
        comment.hidden_at = None
        comment.hidden_reason = None

    try:
        db.commit()
        db.refresh(comment)
    except IntegrityError:
        db.rollback()
        raise
    return comment


def validate_post_exists(db: Session, post_id: int) -> Post:
    post = db.get(Post, post_id)

    if post is None:
        raise ValueError("Post not found")

    return post

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

def to_comment_response(comment: Comment, current_user: User) -> CommentResponse:
    return CommentResponse(
        id=comment.id,
        content=(
            "관리자에 의해 숨김 처리된 댓글입니다."
            if comment.is_hidden
            else comment.content
        ),
        post_id=comment.post_id,
        author_name=(
            "알 수 없음"
            if comment.is_hidden
            else "익명" if comment.is_anonymous else comment.author.name
        ),
        parent_comment_id=comment.parent_comment_id,
        is_anonymous=comment.is_anonymous,
        commented_at=comment.commented_at,
        updated_at=comment.updated_at,
        is_mine=comment.author_id == current_user.id,
        is_hidden=comment.is_hidden,
    )
