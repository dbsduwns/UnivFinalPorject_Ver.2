from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.chat import (
    ChatMessageCreate,
    ChatMessageResponse,
    MessengerRoomCreate,
    ChatRoomResponse,
    ChatRoomUpdate,
    MessengerSendResponse,
    RoomNotificationResponse,
    RoomNotificationUpdate,
)
from app.services import chat as chat_service

router = APIRouter(prefix="/api/chat", tags=["chat"])

@router.post("/rooms", response_model=ChatRoomResponse)
def create_room(
    data: MessengerRoomCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return chat_service.create_room(db, current_user, data)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

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

@router.post("/rooms/{room_id}/messages", response_model=MessengerSendResponse)
def send_message(
    room_id: int,
    data: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return {"message": chat_service.send_message(db, current_user, room_id, data)}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

@router.delete("/rooms/{room_id}")
def delete_room(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        chat_service.delete_room(db, current_user, room_id)
        return {"message": "대화방에서 나갔습니다."}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/rooms/{room_id}", response_model=ChatRoomResponse)
def update_room(
    room_id: int,
    data: ChatRoomUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return chat_service.update_room_name(db, current_user, room_id, data.name)
    except ValueError as exc:
        status_code = 404 if str(exc) == "대화방을 찾을 수 없습니다." else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.patch("/rooms/{room_id}/notification", response_model=RoomNotificationResponse)
def update_room_notification(
    room_id: int,
    data: RoomNotificationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        participant = chat_service.update_room_notification(
            db, current_user, room_id, data.is_muted
        )
        return {"room_id": room_id, "is_muted": participant.is_muted}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
