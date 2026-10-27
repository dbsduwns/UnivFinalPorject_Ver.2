from sqlalchemy.orm import Session

from app.models.room_participants import RoomParticipant
from app.models.user import User
from app.models.user_presence import UserPresence
from app.schemas.presence import UserPresenceUpdate


def update_user_presence(
    db: Session,
    user: User,
    data: UserPresenceUpdate,
) -> UserPresence:
    """현재 사용자의 앱·대화방 열람 상태를 생성하거나 갱신한다."""

    active_room_id = data.active_room_id
    if not data.is_app_foreground:
        # 백그라운드 앱은 특정 대화방을 보고 있는 상태가 될 수 없다.
        active_room_id = None

    if active_room_id is not None:
        is_participant = (
            db.query(RoomParticipant.id)
            .filter(
                RoomParticipant.room_id == active_room_id,
                RoomParticipant.user_id == user.id,
            )
            .first()
            is not None
        )
        if not is_participant:
            raise ValueError("참여 중인 대화방만 활성 대화방으로 설정할 수 있습니다.")

    presence = db.query(UserPresence).filter(UserPresence.user_id == user.id).first()
    if presence is None:
        presence = UserPresence(user_id=user.id)
        db.add(presence)

    presence.active_room_id = active_room_id
    presence.is_app_foreground = data.is_app_foreground
    db.commit()
    db.refresh(presence)
    return presence
