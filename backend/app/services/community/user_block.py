from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.community.comment import Comment
from app.models.community.post import Post
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
    comment_id: int | None = None,
    post_id: int | None = None,
) -> UserBlock:
    if (comment_id is None) == (post_id is None):
        raise ValueError("댓글 또는 게시글 중 하나가 필요합니다")
    target_author_id: int
    if comment_id is not None:
        comment = db.get(Comment, comment_id)
        if comment is None:
            raise LookupError("댓글을 찾을 수 없습니다")
        target_author_id = comment.author_id
        if comment.is_hidden:
            raise PermissionError("Comment is hidden. You do not have permission to block")
    else:
        post = db.get(Post, post_id)
        if post is None:
            raise LookupError("게시글을 찾을 수 없습니다")
        target_author_id = post.author_id
        if post.is_hidden:
            raise PermissionError("숨김 처리된 게시글의 작성자는 차단할 수 없습니다")

    if target_author_id == user.id:
        raise PermissionError("자기 자신은 차단할 수 없습니다")

    existing_block = (
        db.query(UserBlock)
        .filter(
            UserBlock.blocker_id == user.id,
            UserBlock.blocked_user_id == target_author_id,
        )
        .first()
    )
    if existing_block is not None:
        raise ValueError("이미 차단한 사용자입니다")

    user_block = UserBlock(
        blocker_id=user.id,
        blocked_user_id=target_author_id,
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
