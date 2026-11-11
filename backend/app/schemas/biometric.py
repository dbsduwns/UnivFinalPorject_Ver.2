from typing import Literal

from pydantic import BaseModel, Field, field_validator


class BiometricRegisterRequest(BaseModel):
    credential: str = Field(min_length=43, max_length=512)
    device_id: str = Field(min_length=16, max_length=128)
    platform: Literal["android", "ios"]

    @field_validator("credential", "device_id")
    @classmethod
    def strip_values(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("값을 입력해 주세요.")
        return value


class BiometricRegisterResponse(BaseModel):
    enabled: bool
    credential_id: int


class BiometricUnlockRequest(BaseModel):
    credential: str = Field(min_length=43, max_length=512)
    device_id: str = Field(min_length=16, max_length=128)

    @field_validator("credential", "device_id")
    @classmethod
    def strip_values(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("값을 입력해 주세요.")
        return value


class BiometricUnlockResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class BiometricLockRequest(BaseModel):
    session_id: str = Field(min_length=20, max_length=128)
