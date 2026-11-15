from typing import Literal

from pydantic import BaseModel


class TelegramLoginRequest(BaseModel):
    init_data: str


class DevLoginRequest(BaseModel):
    telegram_id: int
    first_name: str = "Dev"


class UserInfo(BaseModel):
    id: int
    first_name: str | None = None
    username: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserInfo


class AccessInfo(BaseModel):
    status: Literal["demo", "full"]
    until: str | None = None


class MeResponse(BaseModel):
    id: int
    first_name: str | None = None
    username: str | None = None
    access: AccessInfo
    days_to_exam: int | None = None
    exam_date: str | None = None