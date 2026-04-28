from pydantic import BaseModel
from datetime import date, datetime

class DailyMenuResponse(BaseModel):
    id: int
    menu_date: date
    image_url: str | None = None
    crawled_at: datetime | None = None

    model_config = {
        "from_attributes": True
    }
