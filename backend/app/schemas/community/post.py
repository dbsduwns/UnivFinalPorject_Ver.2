from datetime import datetime
from pydantic import BaseModel, ConfigDict

class CreatePost(BaseModel):
    title: str
    content: str
    is_anonymous: bool = False

class UpdatePost(BaseModel):
    title: str | None = None
    content: str | None = None
    is_anonymous: bool | None = None

class PostResponse(BaseModel):
    id: int
    slug: str
    board_slug: str
    title: str
    content: str
    author_name: str
    is_anonymous: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
