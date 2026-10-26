"""회원 탈퇴 시 계정에 연결된 데이터를 정리하는 서비스."""

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.ai_chat_room import ChatRoom
from app.models.ai_message import Message
from app.models.completed_course import CompletedCourse
from app.models.community.comment import Comment
from app.models.community.comment_report import CommentReport
from app.models.community.like import CommentLike, PostLike
from app.models.community.post import Post
from app.models.community.user_block import UserBlock
from app.models.commute import CommuteProfile
from app.models.custom_schedule import CustomSchedule
from app.models.friend_invite import FriendInvite
from app.models.friendship import Friendship
from app.models.messenger import Messenger
from app.models.notice_read import NoticeRead
from app.models.notification_setting import NotificationSetting
from app.models.room_messengers import RoomMessenger
from app.models.room_participants import RoomParticipant
from app.models.timetable import Timetable
from app.models.timetable_course import TimetableCourse
from app.models.user import User
from app.models.wizard_selection import WizardSelection


def delete_account(db: Session, user: User) -> None:
    """사용자와 사용자가 생성한 모든 서비스 데이터를 하나의 트랜잭션으로 삭제한다."""
    user_id = user.id

    # 개인 시간표와 그 하위 항목
    timetable_ids = select(Timetable.id).where(Timetable.user_id == user_id)
    db.query(CustomSchedule).filter(CustomSchedule.timetable_id.in_(timetable_ids)).delete(
        synchronize_session=False
    )
    db.query(TimetableCourse).filter(TimetableCourse.timetable_id.in_(timetable_ids)).delete(
        synchronize_session=False
    )
    db.query(Timetable).filter(Timetable.user_id == user_id).delete(synchronize_session=False)

    # AI 채팅방과 메시지
    ai_room_ids = select(ChatRoom.id).where(ChatRoom.user_id == user_id)
    db.query(Message).filter(Message.chat_room_id.in_(ai_room_ids)).delete(synchronize_session=False)
    db.query(ChatRoom).filter(ChatRoom.user_id == user_id).delete(synchronize_session=False)

    # 커뮤니티 게시글·댓글 및 연결된 좋아요·신고 기록
    owned_post_ids = select(Post.id).where(Post.author_id == user_id)
    deleted_comment_ids = select(Comment.id).where(
        or_(Comment.author_id == user_id, Comment.post_id.in_(owned_post_ids))
    )
    db.query(CommentReport).filter(
        or_(
            CommentReport.reporter_id == user_id,
            CommentReport.reported_user_id == user_id,
            CommentReport.reviewed_by_id == user_id,
            CommentReport.comment_id.in_(deleted_comment_ids),
        )
    ).delete(synchronize_session=False)
    db.query(CommentLike).filter(
        or_(CommentLike.user_id == user_id, CommentLike.comment_id.in_(deleted_comment_ids))
    ).delete(synchronize_session=False)
    db.query(PostLike).filter(
        or_(PostLike.user_id == user_id, PostLike.post_id.in_(owned_post_ids))
    ).delete(synchronize_session=False)

    # 다른 회원이 작성한 답글은 유지하되, 탈퇴 회원의 댓글과의 부모 연결만 끊는다.
    db.query(Comment).filter(
        Comment.parent_comment_id.in_(deleted_comment_ids),
        Comment.author_id != user_id,
        ~Comment.post_id.in_(owned_post_ids),
    ).update({Comment.parent_comment_id: None}, synchronize_session=False)
    db.query(Comment).filter(Comment.author_id == user_id).delete(synchronize_session=False)
    db.query(Post).filter(Post.author_id == user_id).delete(synchronize_session=False)

    # 친구·차단·메신저 데이터
    db.query(Friendship).filter(
        or_(Friendship.requester_id == user_id, Friendship.addressee_id == user_id)
    ).delete(synchronize_session=False)
    db.query(FriendInvite).filter(FriendInvite.inviter_id == user_id).delete(synchronize_session=False)
    db.query(UserBlock).filter(
        or_(UserBlock.blocker_id == user_id, UserBlock.blocked_user_id == user_id)
    ).delete(synchronize_session=False)
    db.query(Messenger).filter(Messenger.sender_id == user_id).delete(synchronize_session=False)
    participant_room_ids = [
        room_id
        for (room_id,) in db.query(RoomParticipant.room_id)
        .filter(RoomParticipant.user_id == user_id)
        .all()
    ]
    db.query(RoomParticipant).filter(RoomParticipant.user_id == user_id).delete(
        synchronize_session=False
    )

    # 참가자가 남지 않은 메신저 방도 하위 메시지와 함께 정리한다.
    if participant_room_ids:
        empty_room_ids = (
            select(RoomMessenger.id)
            .where(RoomMessenger.id.in_(participant_room_ids))
            .outerjoin(RoomParticipant, RoomParticipant.room_id == RoomMessenger.id)
            .group_by(RoomMessenger.id)
            .having(func.count(RoomParticipant.id) == 0)
        )
        db.query(Messenger).filter(Messenger.room_messenger_id.in_(empty_room_ids)).delete(
            synchronize_session=False
        )
        db.query(RoomMessenger).filter(RoomMessenger.id.in_(empty_room_ids)).delete(
            synchronize_session=False
        )

    # 남은 개인 설정·활동 기록
    db.query(CompletedCourse).filter(CompletedCourse.user_id == user_id).delete(
        synchronize_session=False
    )
    db.query(CommuteProfile).filter(CommuteProfile.user_id == user_id).delete(
        synchronize_session=False
    )
    db.query(NoticeRead).filter(NoticeRead.user_id == user_id).delete(synchronize_session=False)
    db.query(NotificationSetting).filter(NotificationSetting.user_id == user_id).delete(
        synchronize_session=False
    )
    db.query(WizardSelection).filter(WizardSelection.user_id == user_id).delete(
        synchronize_session=False
    )

    db.delete(user)
    db.commit()
