from pydantic import BaseModel
from datetime import date, datetime

class DailyMenuResponse(BaseModel):
    id: int
    menu_date: date
    image_url: str
    crawled_at: datetime

    class Config:
        from_attributes = True