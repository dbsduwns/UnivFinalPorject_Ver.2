from pydantic import BaseModel, Field
from datetime import date, datetime

class MenuItemResponse(BaseModel):
    id: int
    name: str
    meal_type: str | None = None
    corner: str | None = None
    price: int | None = None
    calories: int | None = None

    model_config = {"from_attributes": True}


class DailyMenuResponse(BaseModel):
    id: int
    menu_date: date
    image_url: str | None = None
    ocr_status: str
    crawled_at: datetime | None = None
    menu_items: list[MenuItemResponse] = Field(default_factory=list)

    model_config = {
        "from_attributes": True
    }
