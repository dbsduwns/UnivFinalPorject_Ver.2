from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


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


class ChatNavigationTarget(BaseModel):
    type: Literal["notice", "meal", "shuttle"]
    label: str
    params: dict[str, str]


class ChatMessageResponse(BaseModel):
    id: int
    chat_room_id: int
    role: str
    content: str
    navigation_targets: list[ChatNavigationTarget] = Field(default_factory=list)
    created_at: datetime | None = None

    @field_validator("navigation_targets", mode="before")
    @classmethod
    def normalize_navigation_targets(cls, value):
        return value or []

    model_config = {
        "from_attributes": True
    }


class ChatSendResponse(BaseModel):
    room: ChatRoomResponse
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse
