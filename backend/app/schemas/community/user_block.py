from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CreateUserBlock(BaseModel):
    # 댓글 작성자의 실제 ID를 노출하지 않고 comment_id로 차단합니다.
    comment_id: int = Field(gt=0)


class UserBlockResponse(BaseModel):
    id: int
    created_at: datetime
    blocked_user_id: int | None = None
    display_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class UserBlockListItem(UserBlockResponse):
    display_name: str = "차단한 사용자"


class UserBlockStatusResponse(BaseModel):
    is_blocked: bool
    block_id: int | None = None
