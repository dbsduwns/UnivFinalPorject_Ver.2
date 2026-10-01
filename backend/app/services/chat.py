from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.messenger import Messenger
from app.models.room_messengers import RoomMessenger
from app.models.room_participants import RoomParticipant
from app.models.user import User
from app.schemas.chat import ChatMessageCreate, MessengerRoomCreate
from app.services.friend import check_is_friend


def _direct_key(user_ids: set[int]) -> str:
    return ":".join(str(user_id) for user_id in sorted(user_ids))


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
            return existing_room

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
                return existing_room
        raise

    db.refresh(room)
    return room


def get_my_rooms(db: Session, user: User) -> list[RoomMessenger]:
    return (
        db.query(RoomMessenger)
        .join(RoomParticipant, RoomParticipant.room_id == RoomMessenger.id)
        .options(selectinload(RoomMessenger.participants).selectinload(RoomParticipant.user))
        .filter(RoomParticipant.user_id == user.id)
        .order_by(RoomMessenger.updated_at.desc(), RoomMessenger.id.desc())
        .all()
    )


def get_my_room(db: Session, user: User, room_id: int) -> RoomMessenger | None:
    return (
        db.query(RoomMessenger)
        .join(RoomParticipant, RoomParticipant.room_id == RoomMessenger.id)
        .options(selectinload(RoomMessenger.participants).selectinload(RoomParticipant.user))
        .filter(RoomMessenger.id == room_id, RoomParticipant.user_id == user.id)
        .first()
    )


def get_room_messages(db: Session, user: User, room_id: int) -> list[Messenger]:
    if get_my_room(db, user, room_id) is None:
        raise ValueError("대화방을 찾을 수 없습니다.")
    return (
        db.query(Messenger)
        .filter(Messenger.room_messenger_id == room_id)
        .order_by(Messenger.id.asc())
        .all()
    )


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
