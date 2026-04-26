from pydantic import BaseModel
from datetime import datetime

class NoticeResponse(BaseModel):
    id: int
    title: str
    content:str
    category: str
    source_url: str | None = None
    is_important: bool
    created_at: datetime
    published_at: datetime | None = None

    class Config:
        from_attributes = True

class NoticeUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    category: str | None = None

    class Config:
        from_attributes = True
