from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator


Platform = Literal["android"]


class AppReleaseCreate(BaseModel):
    platform: Platform = "android"
    version_code: int = Field(ge=1)
    version_name: str = Field(min_length=1, max_length=50)
    minimum_version_code: int = Field(default=1, ge=1)
    apk_url: HttpUrl
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-fA-F]{64}$")
    release_notes: list[str] = Field(default_factory=list, max_length=30)
    mandatory: bool = False
    is_active: bool = True

    @field_validator("apk_url")
    @classmethod
    def validate_https_url(cls, value: HttpUrl):
        if value.scheme != "https":
            raise ValueError("APK URL은 HTTPS 주소여야 합니다.")
        return value

    @model_validator(mode="after")
    def validate_version_range(self):
        if self.minimum_version_code > self.version_code:
            raise ValueError("minimum_version_code는 version_code보다 클 수 없습니다.")
        return self


class AppReleaseUpdate(BaseModel):
    version_name: str | None = Field(default=None, min_length=1, max_length=50)
    minimum_version_code: int | None = Field(default=None, ge=1)
    apk_url: HttpUrl | None = None
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-fA-F]{64}$")
    release_notes: list[str] | None = Field(default=None, max_length=30)
    mandatory: bool | None = None
    is_active: bool | None = None

    @field_validator("apk_url")
    @classmethod
    def validate_https_url(cls, value: HttpUrl | None):
        if value is not None and value.scheme != "https":
            raise ValueError("APK URL은 HTTPS 주소여야 합니다.")
        return value


class AppReleaseResponse(BaseModel):
    id: int
    platform: str
    version_code: int
    version_name: str
    minimum_version_code: int
    apk_url: str
    sha256: str | None = None
    release_notes: list[str]
    mandatory: bool
    is_active: bool
    published_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AppUpdateCheckResponse(BaseModel):
    current_version_code: int
    update_available: bool
    mandatory: bool
    latest_release: AppReleaseResponse | None = None
