import json
from collections.abc import AsyncIterator
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.ai_chat_room import ChatRoom
from app.models.ai_message import Message
from app.models.user import User
from app.schemas.ai_chat import (
    ChatMessageCreate,
    ChatMessageResponse,
    ChatRoomCreate,
    ChatRoomResponse,
)
from app.core.ai_bot import campus_ai_bot
from app.services.timetable_context import (
    build_main_timetable_context,
    needs_timetable_context,
)
from app.services.ai_fallback import build_ai_fallback_reply


AI_REQUEST_LIMIT = 4
AI_REQUEST_WINDOW = timedelta(minutes=1)


class AIRequestLimitExceeded(ValueError):
    pass


def encode_stream_event(event: dict[str, Any]) -> bytes:
    """Encode one NDJSON event using ASCII-safe JSON for mobile stream readers."""
    return (json.dumps(event, ensure_ascii=True, default=str) + "\n").encode("ascii")


def _serialize_message(message: Message) -> dict[str, Any]:
    return ChatMessageResponse.model_validate(message).model_dump(mode="json")


def _serialize_room(room: ChatRoom) -> dict[str, Any]:
    return ChatRoomResponse.model_validate(room).model_dump(mode="json")


def _build_personal_context(db: Session, user: User, content: str) -> str | None:
    if not needs_timetable_context(content):
        return None

    personal_context = build_main_timetable_context(db, user)
    print(
        f"[AI Bot] 개인 시간표 Context 추가: user_id={user.id}, "
        f"length={len(personal_context)}",
        flush=True,
    )
    return personal_context


def _build_conversation_context(
    db: Session,
    room_id: int,
    before_message_id: int,
    limit: int = 8,
) -> str | None:
    """Return only the recent history from this room for follow-up questions."""
    messages = (
        db.query(Message)
        .filter(
            Message.chat_room_id == room_id,
            Message.id < before_message_id,
        )
        .order_by(Message.id.desc())
        .limit(limit)
        .all()
    )
    if not messages:
        return None

    messages.reverse()
    lines = []
    for message in messages:
        role = "사용자" if message.role == "user" else "AI"
        content = (message.content or "").strip()
        if content:
            lines.append(f"{role}: {content[:2000]}")
    return "\n".join(lines) if lines else None


def _set_initial_room_title(room: ChatRoom, content: str) -> None:
    if room.title in {"새 채팅", "새로운 채팅"}:
        room.title = content[:20] + ("..." if len(content) > 20 else "")


def enforce_ai_request_limit(db: Session, user: User) -> None:
    """Use the shared database so the limit applies across Cloud Run instances."""
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
    personal_context = _build_personal_context(db, user, data.content)
    conversation_context = _build_conversation_context(db, room.id, user_message.id)

    navigation_targets: list[dict[str, Any]] = []
    reply = await campus_ai_bot.ask(
        data.content,
        personal_context=personal_context,
        conversation_context=conversation_context,
        on_navigation_targets=navigation_targets.extend,
    )
    print(f"DEBUG: [chat_service] AI bot replied. Saving assistant message...")

    assistant_message = Message(
        chat_room_id=room.id,
        role="assistant",
        content=reply,
        navigation_targets=navigation_targets,
    )
    db.add(assistant_message)

    # 채팅방 제목이 기본값이면 첫 질문으로 업데이트 (최대 20자)
    _set_initial_room_title(room, data.content)

    db.commit()
    db.refresh(room)
    db.refresh(assistant_message)
    return room, user_message, assistant_message


def prepare_stream_message(
    db: Session,
    user: User,
    room_id: int,
    data: ChatMessageCreate,
) -> tuple[ChatRoom, Message, str | None]:
    """Validate the request and persist its user message before streaming starts."""
    room = get_my_room(db, user, room_id)
    if not room:
        raise ValueError("Chat room not found")

    enforce_ai_request_limit(db, user)
    personal_context = _build_personal_context(db, user, data.content)

    user_message = Message(
        chat_room_id=room.id,
        role="user",
        content=data.content,
    )
    db.add(user_message)
    _set_initial_room_title(room, data.content)
    db.commit()
    db.refresh(room)
    db.refresh(user_message)
    conversation_context = _build_conversation_context(db, room.id, user_message.id)
    return room, user_message, personal_context, conversation_context


async def stream_message(
    room: ChatRoom,
    user_message: Message,
    question: str,
    *,
    personal_context: str | None = None,
    conversation_context: str | None = None,
) -> AsyncIterator[bytes]:
    """Stream one assistant reply as NDJSON and persist it after completion."""
    yield encode_stream_event(
        {
            "type": "start",
            "room": _serialize_room(room),
            "user_message": _serialize_message(user_message),
        }
    )
    yield encode_stream_event({"type": "status", "status": "searching"})

    chunks: list[str] = []
    navigation_targets: list[dict[str, Any]] = []
    generation_started = False
    try:
        async for chunk in campus_ai_bot.astream_answer(
            question,
            personal_context=personal_context,
            conversation_context=conversation_context,
            on_navigation_targets=navigation_targets.extend,
        ):
            if not generation_started:
                generation_started = True
                yield encode_stream_event(
                    {"type": "status", "status": "generating"}
                )
            chunks.append(chunk)
            yield encode_stream_event({"type": "delta", "content": chunk})

        reply = "".join(chunks)
        if not reply:
            raise RuntimeError("AI bot returned an empty response")

        if navigation_targets:
            yield encode_stream_event(
                {"type": "navigation", "targets": navigation_targets}
            )

        with SessionLocal() as stream_db:
            assistant_message = Message(
                chat_room_id=room.id,
                role="assistant",
                content=reply,
                navigation_targets=navigation_targets,
            )
            stream_db.add(assistant_message)
            stream_db.commit()
            stream_db.refresh(assistant_message)
            persisted_room = stream_db.get(ChatRoom, room.id)
            if persisted_room is None:
                raise RuntimeError("Chat room disappeared while saving the response")
            done_event = {
                "type": "done",
                "room": _serialize_room(persisted_room),
                "assistant_message": _serialize_message(assistant_message),
            }

        yield encode_stream_event(done_event)
    except Exception as exc:
        print(
            f"❌ [chat_service] 스트리밍 답변 생성 실패: {exc}",
            flush=True,
        )
        try:
            fallback_reply = build_ai_fallback_reply(question)
            with SessionLocal() as fallback_db:
                assistant_message = Message(
                    chat_room_id=room.id,
                    role="assistant",
                    content=fallback_reply,
                    navigation_targets=[],
                )
                fallback_db.add(assistant_message)
                fallback_db.commit()
                fallback_db.refresh(assistant_message)
                persisted_room = fallback_db.get(ChatRoom, room.id)
                if persisted_room is None:
                    raise RuntimeError("Chat room disappeared while saving the fallback response")

                yield encode_stream_event(
                    {
                        "type": "fallback",
                        "room": _serialize_room(persisted_room),
                        "assistant_message": _serialize_message(assistant_message),
                    }
                )
        except Exception as fallback_exc:
            print(
                f"❌ [chat_service] fallback 답변 저장 실패: {fallback_exc}",
                flush=True,
            )
            yield encode_stream_event(
                {
                    "type": "error",
                    "message": "답변 생성 중 오류가 발생했습니다.",
                }
            )


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
