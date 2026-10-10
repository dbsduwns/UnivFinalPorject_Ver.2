from pydantic import BaseModel


class AdminRoleUpdate(BaseModel):
    is_admin: bool


class AdminRoleResponse(BaseModel):
    id: int
    email: str
    name: str
    is_admin: bool

    model_config = {
        "from_attributes": True,
    }
