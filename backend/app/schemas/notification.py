from datetime import datetime
from typing import Any

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: int
    notification_type: str
    title: str
    body: str
    data: dict[str, Any]
    read_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationCenterResponse(BaseModel):
    items: list[NotificationResponse]
    unread_count: int


class NotificationUnreadCountResponse(BaseModel):
    unread_count: int


class NotificationReadAllResponse(BaseModel):
    updated_count: int
