from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.ai_chat import (
    ChatMessageCreate,
    ChatMessageResponse,
    ChatRoomCreate,
    ChatRoomResponse,
    ChatSendResponse,
)
from app.services import ai_chat as chat_service

router = APIRouter(prefix="/api/ai/chat", tags=["aichat"])


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
    except chat_service.AIRequestLimitExceeded as e:
        raise HTTPException(status_code=429, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/rooms/{room_id}/messages", response_model=ChatSendResponse)
async def send_message(
    room_id: int,
    data: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    print(f"DEBUG: [chat_router] Received request - room_id: {room_id}, user: {current_user.email}")
    try:
        room, user_message, assistant_message = await chat_service.send_message(db, current_user, room_id, data)
        print(f"DEBUG: [chat_router] Message processed successfully")
        return {
            "room": room,
            "user_message": user_message,
            "assistant_message": assistant_message,
        }
    except chat_service.AIRequestLimitExceeded as e:
        print(f"DEBUG: [chat_router] Request limit exceeded: {str(e)}")
        raise HTTPException(status_code=429, detail=str(e)) from e
    except ValueError as e:
        print(f"DEBUG: [chat_router] ValueError: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        print(f"DEBUG: [chat_router] Unexpected Error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/rooms/{room_id}/messages/stream", response_class=StreamingResponse)
async def stream_message(
    room_id: int,
    data: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Stream an AI reply as newline-delimited JSON events."""
    try:
        room, user_message, personal_context, conversation_context = chat_service.prepare_stream_message(
            db,
            current_user,
            room_id,
            data,
        )
    except chat_service.AIRequestLimitExceeded as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        print(f"DEBUG: [chat_router] Stream preparation failed: {exc}")
        raise HTTPException(status_code=500, detail="Internal Server Error") from exc

    event_stream = chat_service.stream_message(
        room,
        user_message,
        data.content,
        personal_context=personal_context,
        conversation_context=conversation_context,
    )
    return StreamingResponse(
        event_stream,
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )


@router.patch("/rooms/{room_id}", response_model=ChatRoomResponse)
def update_room(
    room_id: int,
    data: ChatRoomCreate,  # title만 사용
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return chat_service.update_room_title(db, current_user, room_id, data.title)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/rooms/{room_id}")
def delete_room(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        chat_service.delete_room(db, current_user, room_id)
        return {"message": "Chat room deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
