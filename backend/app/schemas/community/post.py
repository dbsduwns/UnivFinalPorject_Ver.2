from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

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
    is_hidden: bool = False
    is_pinned: bool = False
    created_at: datetime
    updated_at: datetime
    is_mine: bool = False

    model_config = ConfigDict(from_attributes=True)


class AdminPostUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    content: str | None = Field(default=None, min_length=1)
    is_hidden: bool | None = None
    is_pinned: bool | None = None

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
