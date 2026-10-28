from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.messenger import Messenger
from app.models.room_messengers import RoomMessenger
from app.models.room_participants import RoomParticipant
from app.models.user import User
from app.models.user_presence import UserPresence
from app.core.notification import notify_users_by_type_sync
from app.schemas.chat import ChatMessageCreate, ChatRoomResponse, MessengerRoomCreate
from app.services.friend import check_is_friend


PRESENCE_TTL_SECONDS = 60


def _direct_key(user_ids: set[int]) -> str:
    return ":".join(str(user_id) for user_id in sorted(user_ids))


def _with_my_notification_setting(room: RoomMessenger, user_id: int) -> RoomMessenger:
    participant = next((item for item in room.participants if item.user_id == user_id), None)
    room.is_muted = participant.is_muted if participant is not None else False
    return room


def _is_viewing_room(db: Session, user_id: int, room_id: int) -> bool:
    """최근 heartbeat가 있는 사용자가 해당 대화방을 보고 있는지 확인한다."""
    # DB의 TIMESTAMP가 timezone 없이 저장되므로 UTC 기준 naive datetime으로 비교한다.
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=PRESENCE_TTL_SECONDS)).replace(tzinfo=None)
    return (
        db.query(UserPresence.id)
        .filter(
            UserPresence.user_id == user_id,
            UserPresence.active_room_id == room_id,
            UserPresence.is_app_foreground.is_(True),
            UserPresence.last_seen_at >= cutoff,
        )
        .first()
        is not None
    )


def create_room(db: Session, user: User, data: MessengerRoomCreate) -> RoomMessenger:
    participant_ids = set(data.participant_ids)
    participant_ids.add(user.id)

    if len(participant_ids) < 2:
        raise ValueError("대화 상대가 필요합니다.")

    users = db.query(User).filter(User.id.in_(participant_ids), User.is_active.is_(True)).all()
    if len(users) != len(participant_ids):
        raise ValueError("존재하지 않거나 비활성화된 사용자가 포함되어 있습니다.")

    for participant_id in participant_ids - {user.id}:
        if not check_is_friend(db, user.id, participant_id):
            raise PermissionError("친구가 아닌 사용자는 초대할 수 없습니다.")

    is_group = len(participant_ids) > 2
    direct_key = None if is_group else _direct_key(participant_ids)
    if direct_key is not None:
        existing_room = (
            db.query(RoomMessenger)
            .options(selectinload(RoomMessenger.participants).selectinload(RoomParticipant.user))
            .filter(RoomMessenger.direct_key == direct_key)
            .first()
        )
        if existing_room is not None:
            return _with_my_notification_setting(existing_room, user.id)

    room = RoomMessenger(is_group=is_group, name=data.name if is_group else None, direct_key=direct_key)
    room.participants = [RoomParticipant(user_id=participant_id) for participant_id in sorted(participant_ids)]
    try:
        db.add(room)
        db.commit()
    except IntegrityError:
        db.rollback()
        # 동시 요청으로 동일한 1:1 방이 생성된 경우 이미 생성된 방을 재사용합니다.
        if direct_key is not None:
            existing_room = (
                db.query(RoomMessenger)
                .options(selectinload(RoomMessenger.participants).selectinload(RoomParticipant.user))
                .filter(RoomMessenger.direct_key == direct_key)
                .first()
            )
            if existing_room is not None:
                return _with_my_notification_setting(existing_room, user.id)
        raise

    db.refresh(room)
    return _with_my_notification_setting(room, user.id)


def get_my_rooms(db: Session, user: User) -> list[ChatRoomResponse]:
    rooms = (
        db.query(RoomMessenger)
        .join(RoomParticipant, RoomParticipant.room_id == RoomMessenger.id)
        .options(selectinload(RoomMessenger.participants).selectinload(RoomParticipant.user))
        .filter(RoomParticipant.user_id == user.id)
        .order_by(RoomMessenger.updated_at.desc(), RoomMessenger.id.desc())
        .all()
    )

    responses = []
    for room in rooms:
        my_participant = next(
            participant
            for participant in room.participants
            if participant.user_id == user.id
        )

        unread_count = (
            db.query(func.count(Messenger.id))
            .filter(
                Messenger.room_messenger_id == room.id,
                Messenger.sender_id != user.id,
                Messenger.created_at > my_participant.last_read,
            )
            .scalar()
        )

        responses.append(
            ChatRoomResponse(
                id=room.id,
                is_group=room.is_group,
                name=room.name,
                created_at=room.created_at,
                updated_at=room.updated_at,
                participants=room.participants,
                is_muted=my_participant.is_muted,
                unread_count=unread_count,
            )
        )

    return responses



def get_my_room(db: Session, user: User, room_id: int) -> RoomMessenger | None:
    room = (
        db.query(RoomMessenger)
        .join(RoomParticipant, RoomParticipant.room_id == RoomMessenger.id)
        .options(selectinload(RoomMessenger.participants).selectinload(RoomParticipant.user))
        .filter(RoomMessenger.id == room_id, RoomParticipant.user_id == user.id)
        .first()
    )
    return _with_my_notification_setting(room, user.id) if room is not None else None


def get_room_messages(db: Session, user: User, room_id: int) -> list[Messenger]:
    my_room = get_my_room(db, user, room_id)

    if my_room is None:
        raise ValueError("대화방을 찾을 수 없습니다.")

    participant = next(
        item for item in my_room.participants
        if item.user_id == user.id
    )

    messages = (
        db.query(Messenger)
        .filter(Messenger.room_messenger_id == room_id)
        .order_by(Messenger.id.asc())
        .all()
    )

    if messages:
        participant.last_read = messages[-1].created_at
        db.commit()

    return messages


def send_message(db: Session, user: User, room_id: int, data: ChatMessageCreate) -> Messenger:
    room = get_my_room(db, user, room_id)
    if room is None:
        raise ValueError("대화방을 찾을 수 없습니다.")
    if len(room.participants) < 2:
        raise ValueError("다른 참여자가 없어 메시지를 보낼 수 없습니다.")

    message = Messenger(room_messenger_id=room.id, sender_id=user.id, content=data.content)
    db.add(message)
    room.updated_at = func.now()
    db.commit()
    db.refresh(message)

    # 1:1 대화에서만 상대방에게 새 메시지 알림을 보낸다. 메시지 본문은 잠금 화면에 노출하지 않는다.
    if not room.is_group:
        recipient_ids = [
            participant.user_id
            for participant in room.participants
            if (
                participant.user_id != user.id
                and not participant.is_muted
                and not _is_viewing_room(db, participant.user_id, room.id)
            )
        ]
        if recipient_ids:
            notify_users_by_type_sync(
                db,
                "message_alert",
                f"{user.name}님이 메시지를 보냈습니다.",
                "새 메시지가 도착했습니다.",
                {
                    "type": "direct_message",
                    "room_id": room.id,
                    "sender_id": user.id,
                    "recipient_id": recipient_ids[0],
                },
                recipient_ids=recipient_ids,
            )
    return message


def delete_room(db: Session, user: User, room_id: int) -> None:
    room = get_my_room(db, user, room_id)
    if room is None:
        raise ValueError("대화방을 찾을 수 없습니다.")

    participant = next(p for p in room.participants if p.user_id == user.id)
    if len(room.participants) == 1:
        db.delete(room)
    else:
        # 다른 참여자의 메시지는 보존하고 현재 사용자만 방에서 나갑니다.
        if not room.is_group:
            room.direct_key = None
        db.delete(participant)
    db.commit()


def update_room_name(db: Session, user: User, room_id: int, name: str) -> RoomMessenger:
    room = get_my_room(db, user, room_id)
    if room is None:
        raise ValueError("대화방을 찾을 수 없습니다.")
    if not room.is_group:
        raise ValueError("단체 채팅방만 이름을 변경할 수 있습니다.")

    room.name = name
    room.updated_at = func.now()
    db.commit()
    db.refresh(room)
    return _with_my_notification_setting(room, user.id)


def update_room_notification(
    db: Session,
    user: User,
    room_id: int,
    is_muted: bool,
) -> RoomParticipant:
    participant = (
        db.query(RoomParticipant)
        .filter(RoomParticipant.room_id == room_id, RoomParticipant.user_id == user.id)
        .first()
    )
    if participant is None:
        raise ValueError("대화방을 찾을 수 없습니다.")

    participant.is_muted = is_muted
    db.commit()
    db.refresh(participant)
    return participant
