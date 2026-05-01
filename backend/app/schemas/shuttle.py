from datetime import datetime

from pydantic import BaseModel

class ShuttleResponse(BaseModel):
    id: int
    title: str
    file_url: str
    source_url: str | None = None
    semester: str | None = None
    original_filename: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {
        "from_attributes": True
    }


class ShuttleCrawlResponse(BaseModel):
    message: str
    item: ShuttleResponse
