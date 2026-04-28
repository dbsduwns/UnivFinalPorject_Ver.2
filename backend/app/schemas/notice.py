from pydantic import BaseModel
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
    title: str | None = None
    content: str | None = None
    category: str | None = None

    model_config = {
        "from_attributes": True
    }
