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


class AdminUserResponse(AdminRoleResponse):
    student_id: str | None = None
    department: str | None = None
    grade: int | None = None
    is_active: bool
    created_at: datetime | None = None


class AdminUserActiveUpdate(BaseModel):
    is_active: bool


class AdminDashboardResponse(BaseModel):
    total_users: int
    active_users: int
    admin_users: int
    total_posts: int
    hidden_posts: int
    pending_reports: int
    notices: int
    recent_reports: list[dict]
