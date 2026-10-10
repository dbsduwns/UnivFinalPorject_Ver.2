from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from enum import Enum

class CreateComment(BaseModel):
    content: str
    parent_comment_id: int | None = None
    is_anonymous: bool = False

class UpdateComment(BaseModel):
    content: str | None = None
    is_anonymous: bool | None = None

class CommentResponse(BaseModel):
    id: int
    content: str
    post_id: int
    author_name: str
    parent_comment_id: int | None = None
    is_anonymous: bool
    commented_at: datetime
    updated_at: datetime
    is_mine: bool
    is_hidden: bool

    model_config = ConfigDict(from_attributes=True)

class CommentModerationAction(str, Enum):
    HIDE = "hide"
    RESTORE = "restore"


class ModerateComment(BaseModel):
    action: CommentModerationAction
    reason: str | None = Field(default=None, max_length=500) 

class AdminCommentResponse(CommentResponse):
    original_content: str
    hidden_by_id: int | None
    hidden_at: datetime | None
    hidden_reason: str | None
