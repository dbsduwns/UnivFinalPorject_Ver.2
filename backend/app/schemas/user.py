from datetime import datetime
from pydantic import BaseModel, Field, field_validator


EMAIL_PATTERN = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"

class UserSignup(BaseModel):
    email: str = Field(min_length=5, max_length=254, pattern=EMAIL_PATTERN)
    password: str = Field(min_length=8, max_length=72)
    name: str = Field(min_length=2, max_length=50)
    student_id: str = Field(min_length=4, max_length=20)

    @field_validator("email", "name", "student_id")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value cannot be blank.")
        return value

    @field_validator("password")
    @classmethod
    def validate_password_bytes(cls, value: str) -> str:
        # bcrypt safely handles passwords up to 72 UTF-8 bytes.
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 UTF-8 bytes.")
        return value

class UserUpdate(BaseModel):
    name: str | None = None
    student_id: str | None = None
    department: str | None = None
    grade: int | None = None
    biometric_auth: bool = False

class UserLogin(BaseModel):
    email: str
    student_email: str | None = None
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
    student_verified_at: datetime | None = None
    student_email: str | None = None

    model_config = {
        "from_attributes": True
    }

class PasswordResetRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254, pattern=EMAIL_PATTERN)

    @field_validator("email")
    @classmethod
    def strip_email(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Email cannot be blank.")
        return value

class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=8, max_length=72)
    confirm_password: str = Field(min_length=8, max_length=72)

    @field_validator("new_password", "confirm_password")
    @classmethod
    def validate_password_bytes(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 UTF-8 bytes.")
        return value

class PasswordVerifyRequest(BaseModel):
    password: str = Field(min_length=8, max_length=72)

class PasswordChangeRequest(BaseModel):
    current_password: str | None = Field(default=None, min_length=8, max_length=72)
    new_password: str = Field(min_length=8, max_length=72)
    confirm_password: str = Field(min_length=8, max_length=72)
    biometric_auth: bool = False

    @field_validator("current_password", "new_password", "confirm_password")
    @classmethod
    def validate_password_bytes(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 UTF-8 bytes.")
        return value

class PushTokenUpdate(BaseModel):
    expo_push_token: str

class NotificationSettingResponse(BaseModel):
    notice_alert: bool
    shuttle_alert: bool
    cafeteria_alert: bool
    message_alert: bool

    model_config = {
        "from_attributes": True
    }

class NotificationSettingUpdate(BaseModel):
    notice_alert: bool | None = None
    shuttle_alert: bool | None = None
    cafeteria_alert: bool | None = None
    message_alert: bool | None = None
