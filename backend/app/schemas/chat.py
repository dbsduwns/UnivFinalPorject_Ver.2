from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, model_validator

class MessengerRoomCreate(BaseModel):
    participant_ids: list[int] = Field(default_factory=list)
    friend_id: int | None = None
    name: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def normalize_participants(self):
        if self.friend_id is not None and self.friend_id not in self.participant_ids:
            self.participant_ids.append(self.friend_id)
        self.participant_ids = list(dict.fromkeys(self.participant_ids))
        if not self.participant_ids:
            raise ValueError("대화 상대가 필요합니다.")
        if any(user_id <= 0 for user_id in self.participant_ids):
            raise ValueError("참여자 ID는 양수여야 합니다.")
        if self.name is not None:
            self.name = self.name.strip() or None
        return self


class UserSummaryResponse(BaseModel):
    id: int
    name: str
    avatar_url: str | None = None

    model_config = ConfigDict(from_attributes=True)

class ParticipantResponse(BaseModel):
    id: int
    user_id: int
    last_read: datetime | None = None
    user: UserSummaryResponse | None = None

    model_config = ConfigDict(from_attributes=True)

class ChatRoomResponse(BaseModel):
    id: int
    is_group: bool
    name: str | None = None
    created_at: datetime
    updated_at: datetime
    participants: list[ParticipantResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ChatMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=10000)

    @model_validator(mode="after")
    def validate_content(self):
        if not self.content.strip():
            raise ValueError("메시지 내용을 입력해 주세요.")
        return self

class ChatMessageResponse(BaseModel):
    id: int
    room_messenger_id: int
    sender_id: int
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatRoomDetailResponse(ChatRoomResponse):
    messages: list[ChatMessageResponse] = Field(default_factory=list)


class MessengerSendResponse(BaseModel):
    message: ChatMessageResponse
