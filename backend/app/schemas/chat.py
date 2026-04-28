from datetime import datetime

from pydantic import BaseModel


class ChatRoomCreate(BaseModel):
    title: str | None = None


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
    content: str


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


class ChatDemoRequest(BaseModel):
    message: str


class ChatDemoResponse(BaseModel):
    reply: str
    provider: str = "demo"
