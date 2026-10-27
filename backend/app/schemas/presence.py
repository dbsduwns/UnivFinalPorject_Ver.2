from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserPresenceUpdate(BaseModel):
    """앱이 대화방 진입·이탈 또는 heartbeat 때 전송하는 현재 상태입니다."""

    active_room_id: int | None = Field(default=None, gt=0)
    is_app_foreground: bool = True


class UserPresenceResponse(BaseModel):
    id: int
    user_id: int
    active_room_id: int | None = None
    is_app_foreground: bool
    last_seen_at: datetime

    model_config = ConfigDict(from_attributes=True)
