from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.community.comment import Comment
from app.models.community.user_block import UserBlock
from app.models.user import User


def get_user_blocks(
    db: Session,
    user: User,
    skip: int = 0,
    limit: int = 20,
) -> list[UserBlock]:
    return (
        db.query(UserBlock)
        .filter(UserBlock.blocker_id == user.id)
        .order_by(UserBlock.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_user_block(
    db: Session,
    user: User,
    comment_id: int,
) -> UserBlock:
    comment = db.get(Comment, comment_id)
    if comment is None:
        raise LookupError("댓글을 찾을 수 없습니다")

    if comment.author_id == user.id:
        raise PermissionError("자기 자신은 차단할 수 없습니다")

    if comment.is_hidden:
        raise PermissionError(
            "Comment is hidden. You do not have permission to block"
        )

    existing_block = (
        db.query(UserBlock)
        .filter(
            UserBlock.blocker_id == user.id,
            UserBlock.blocked_user_id == comment.author_id,
        )
        .first()
    )
    if existing_block is not None:
        raise ValueError("이미 차단한 사용자입니다")

    user_block = UserBlock(
        blocker_id=user.id,
        blocked_user_id=comment.author_id,
    )

    try:
        db.add(user_block)
        db.commit()
        db.refresh(user_block)
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("이미 차단한 사용자입니다") from exc

    return user_block


def delete_user_block(
    db: Session,
    user: User,
    block_id: int,
) -> None:
    block = (
        db.query(UserBlock)
        .filter(
            UserBlock.id == block_id,
            UserBlock.blocker_id == user.id,
        )
        .first()
    )
    if block is None:
        raise LookupError("차단 정보를 찾을 수 없습니다")

    try:
        db.delete(block)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
