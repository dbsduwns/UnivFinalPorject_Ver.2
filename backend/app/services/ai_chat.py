from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.ai_chat_room import ChatRoom
from app.models.ai_message import Message
from app.models.user import User
from app.schemas.ai_chat import ChatMessageCreate, ChatRoomCreate
from app.core.ai_bot import campus_ai_bot
from app.services.timetable_context import (
    build_main_timetable_context,
    needs_timetable_context,
)


AI_REQUEST_LIMIT = 4
AI_REQUEST_WINDOW = timedelta(minutes=1)


class AIRequestLimitExceeded(ValueError):
    pass


def enforce_ai_request_limit(db: Session, user: User) -> None:
    """Use the shared database so the limit applies across Cloud Run instances."""
    # Message.created_at is a database TIMESTAMP without timezone.
    cutoff = datetime.utcnow() - AI_REQUEST_WINDOW
    request_count = (
        db.query(Message)
        .join(ChatRoom, Message.chat_room_id == ChatRoom.id)
        .filter(
            ChatRoom.user_id == user.id,
            Message.role == "user",
            Message.created_at >= cutoff,
        )
        .count()
    )
    if request_count >= AI_REQUEST_LIMIT:
        raise AIRequestLimitExceeded("AI requests are limited to 4 per minute. Please try again shortly.")


def create_room(db: Session, user: User, data: ChatRoomCreate) -> ChatRoom:
    room = ChatRoom(user_id=user.id, title=data.title or "새 채팅")
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


def get_my_rooms(db: Session, user: User) -> list[ChatRoom]:
    return db.query(ChatRoom).filter(ChatRoom.user_id == user.id).order_by(ChatRoom.id.desc()).all()


def get_my_room(db: Session, user: User, room_id: int) -> ChatRoom | None:
    print(f"DEBUG: get_my_room - searching for room_id: {room_id} with user_id: {user.id}")
    room = db.query(ChatRoom).filter(ChatRoom.id == room_id, ChatRoom.user_id == user.id).first()
    if room:
        print(f"DEBUG: Found room ID {room.id}")
    else:
        print(f"DEBUG: Room NOT found for this user")
    return room


def get_room_messages(db: Session, user: User, room_id: int) -> list[Message]:
    room = get_my_room(db, user, room_id)
    if not room:
        raise ValueError("Chat room not found")

    return db.query(Message).filter(Message.chat_room_id == room_id).order_by(Message.id.asc()).all()


async def send_message(db: Session, user: User, room_id: int, data: ChatMessageCreate) -> tuple[ChatRoom, Message, Message]:
    room = get_my_room(db, user, room_id)
    if not room:
        raise ValueError("Chat room not found")

    enforce_ai_request_limit(db, user)

    user_message = Message(chat_room_id=room.id, role="user", content=data.content)
    db.add(user_message)
    # AI 응답을 기다리는 동안 DB 세션을 점유하지 않도록 먼저 커밋
    db.commit()
    db.refresh(user_message)

    # AI 봇에게 RAG 기반 질문 답변 요청
    print(f"DEBUG: [chat_service] Calling AI bot for room {room_id}...")
    personal_context = None
    if needs_timetable_context(data.content):
        personal_context = build_main_timetable_context(db, user)
        print(
            f"[AI Bot] 개인 시간표 Context 추가: user_id={user.id}, "
            f"length={len(personal_context)}",
            flush=True,
        )

    reply = await campus_ai_bot.ask(
        data.content,
        personal_context=personal_context,
    )
    print(f"DEBUG: [chat_service] AI bot replied. Saving assistant message...")

    assistant_message = Message(chat_room_id=room.id, role="assistant", content=reply)
    db.add(assistant_message)

    # 채팅방 제목이 기본값이면 첫 질문으로 업데이트 (최대 20자)
    if room.title == "새 채팅" or room.title == "새로운 채팅":
        room.title = data.content[:20] + ("..." if len(data.content) > 20 else "")

    db.commit()
    db.refresh(room)
    db.refresh(assistant_message)
    return room, user_message, assistant_message


async def demo_reply(message: str) -> str:
    # 데모 모드에서도 AI 봇 사용
    return await campus_ai_bot.ask(message)


def delete_room(db: Session, user: User, room_id: int):
    room = get_my_room(db, user, room_id)
    if not room:
        raise ValueError("Chat room not found")
    
    # 메시지들도 같이 삭제됨 (ondelete cascade 설정이 되어있는지 확인 필요하지만, 일단 명시적으로 삭제하거나 cascade 믿음)
    db.delete(room)
    db.commit()
    return True


def update_room_title(db: Session, user: User, room_id: int, title: str) -> ChatRoom:
    room = get_my_room(db, user, room_id)
    if not room:
        raise ValueError("Chat room not found")
    
    room.title = title
    db.commit()
    db.refresh(room)
    return room
