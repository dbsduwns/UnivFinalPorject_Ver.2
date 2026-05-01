from sqlalchemy.orm import Session

from app.models.chat_room import ChatRoom
from app.models.message import Message
from app.models.user import User
from app.schemas.chat import ChatMessageCreate, ChatRoomCreate
from app.core.ai_bot import campus_ai_bot


def create_room(db: Session, user: User, data: ChatRoomCreate) -> ChatRoom:
    room = ChatRoom(user_id=user.id, title=data.title or "새 채팅")
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


def get_my_rooms(db: Session, user: User) -> list[ChatRoom]:
    return db.query(ChatRoom).filter(ChatRoom.user_id == user.id).order_by(ChatRoom.id.desc()).all()


def get_my_room(db: Session, user: User, room_id: int) -> ChatRoom | None:
    return db.query(ChatRoom).filter(ChatRoom.id == room_id, ChatRoom.user_id == user.id).first()


def get_room_messages(db: Session, user: User, room_id: int) -> list[Message]:
    room = get_my_room(db, user, room_id)
    if not room:
        raise ValueError("Chat room not found")

    return db.query(Message).filter(Message.chat_room_id == room_id).order_by(Message.id.asc()).all()


async def send_message(db: Session, user: User, room_id: int, data: ChatMessageCreate) -> tuple[ChatRoom, Message, Message]:
    room = get_my_room(db, user, room_id)
    if not room:
        raise ValueError("Chat room not found")

    user_message = Message(chat_room_id=room.id, role="user", content=data.content)
    db.add(user_message)
    db.flush()

    # AI 봇에게 RAG 기반 질문 답변 요청
    reply = await campus_ai_bot.ask(data.content)
    assistant_message = Message(chat_room_id=room.id, role="assistant", content=reply)
    db.add(assistant_message)

    db.commit()
    db.refresh(room)
    db.refresh(user_message)
    db.refresh(assistant_message)
    return room, user_message, assistant_message


async def demo_reply(message: str) -> str:
    # 데모 모드에서도 AI 봇 사용
    return await campus_ai_bot.ask(message)
