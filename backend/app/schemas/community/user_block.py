from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CreateUserBlock(BaseModel):
    # 댓글 작성자의 실제 ID를 노출하지 않고 comment_id로 차단합니다.
    comment_id: int = Field(gt=0)


class UserBlockResponse(BaseModel):
    # 익명 작성자 식별 방지를 위해 blocked_user_id는 응답하지 않습니다.
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserBlockListItem(UserBlockResponse):
    display_name: str = "차단한 사용자"


class UserBlockStatusResponse(BaseModel):
    is_blocked: bool
    block_id: int | None = None
