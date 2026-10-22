from datetime import datetime

from pydantic import BaseModel, Field


class ChatRoomCreate(BaseModel):
    title: str | None = Field(default=None, max_length=60)


class ChatRoomResponse(BaseModel):
    id: int
    user_id: int
    title: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {
        "from_attributes": True
    }


class ChatMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=500)


class ChatMessageResponse(BaseModel):
    id: int
    chat_room_id: int
    role: str
    content: str
    created_at: datetime | None = None

    model_config = {
        "from_attributes": True
    }


class ChatSendResponse(BaseModel):
    room: ChatRoomResponse
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse
