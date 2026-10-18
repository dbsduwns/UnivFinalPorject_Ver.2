from pydantic import BaseModel
from datetime import datetime


class AdminRoleUpdate(BaseModel):
    is_admin: bool


class AdminUserBlockResponse(BaseModel):
    id: int
    blocker_id: int
    blocked_user_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminRoleResponse(BaseModel):
    id: int
    email: str
    name: str
    is_admin: bool

    model_config = {
        "from_attributes": True,
    }
