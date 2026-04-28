from sqlalchemy.orm import Session

from app.models.chat_room import ChatRoom
from app.models.message import Message
from app.models.user import User
from app.schemas.chat import ChatMessageCreate, ChatRoomCreate


class DemoChatProvider:
    name = "demo"

    def generate_reply(self, message: str) -> str:
        normalized = message.strip()
        if not normalized:
            return "질문 내용을 입력해 주세요."

        if "공지" in normalized:
            return "공지사항은 /api/notices API로 조회할 수 있어요. 키워드 검색도 지원합니다."
        if "식단" in normalized or "학식" in normalized:
            return "식단은 /api/daily-menus/?date=YYYY-MM-DD 형식으로 날짜별 이미지 URL을 조회할 수 있어요."
        if "시간표" in normalized:
            return "시간표는 /api/timetables API에서 생성하고, custom-schedules로 개인 일정을 관리할 수 있어요."

        return f"데모 챗봇 응답입니다. 받은 메시지: {normalized}"


chat_provider = DemoChatProvider()


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


def send_message(db: Session, user: User, room_id: int, data: ChatMessageCreate) -> tuple[ChatRoom, Message, Message]:
    room = get_my_room(db, user, room_id)
    if not room:
        raise ValueError("Chat room not found")

    user_message = Message(chat_room_id=room.id, role="user", content=data.content)
    db.add(user_message)
    db.flush()

    reply = chat_provider.generate_reply(data.content)
    assistant_message = Message(chat_room_id=room.id, role="assistant", content=reply)
    db.add(assistant_message)

    db.commit()
    db.refresh(room)
    db.refresh(user_message)
    db.refresh(assistant_message)
    return room, user_message, assistant_message


def demo_reply(message: str) -> str:
    return chat_provider.generate_reply(message)
