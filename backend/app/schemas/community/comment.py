from datetime import datetime
from pydantic import BaseModel, ConfigDict

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

    model_config = ConfigDict(from_attributes=True)
