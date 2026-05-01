from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.chat import (
    ChatDemoRequest,
    ChatDemoResponse,
    ChatMessageCreate,
    ChatMessageResponse,
    ChatRoomCreate,
    ChatRoomResponse,
    ChatSendResponse,
)
from app.services import chat as chat_service

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/demo", response_model=ChatDemoResponse)
async def demo_chat(data: ChatDemoRequest):
    reply = await chat_service.demo_reply(data.message)
    return {"reply": reply, "provider": "ai_bot"}


@router.post("/rooms", response_model=ChatRoomResponse)
def create_room(
    data: ChatRoomCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return chat_service.create_room(db, current_user, data)


@router.get("/rooms", response_model=list[ChatRoomResponse])
def get_my_rooms(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return chat_service.get_my_rooms(db, current_user)


@router.get("/rooms/{room_id}/messages", response_model=list[ChatMessageResponse])
def get_room_messages(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return chat_service.get_room_messages(db, current_user, room_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/rooms/{room_id}/messages", response_model=ChatSendResponse)
async def send_message(
    room_id: int,
    data: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        room, user_message, assistant_message = await chat_service.send_message(db, current_user, room_id, data)
        return {
            "room": room,
            "user_message": user_message,
            "assistant_message": assistant_message,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
