from pydantic import BaseModel

class UserSignup(BaseModel):
    email: str
    password: str
    name: str

class UserLogin(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    refresh_token: str
    access_token: str

class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    department: str | None = None
    grade: int | None = None
    is_admin: bool = False

    model_config = {
        "from_attributes": True
    }

