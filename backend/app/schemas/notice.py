from pydantic import BaseModel, Field
from datetime import datetime

class NoticeResponse(BaseModel):
    id: int
    title: str
    content: str | None = None
    category: str
    source_url: str | None = None
    attachment_url: str | None = None
    is_important: bool
    published_at: datetime | None = None
    crawled_at: datetime | None = None

    model_config = {
        "from_attributes": True
    }

class NoticeUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    content: str | None = None
    category: str | None = Field(default=None, min_length=1, max_length=50)
    is_important: bool | None = None

    model_config = {
        "from_attributes": True
    }


class NoticeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    content: str = Field(min_length=1)
    category: str = Field(min_length=1, max_length=50)
    is_important: bool = False
