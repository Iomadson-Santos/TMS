from datetime import datetime

from pydantic import Field

from app.schemas.base import ORMModel
from app.schemas.user import UserRead


class BrowserSession(ORMModel):
    expires_in: int
    refresh_expires_in: int
    user: UserRead


class Token(ORMModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserRead


class PasswordChange(ORMModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class SessionRead(ORMModel):
    id: str
    created_at: datetime
    last_used_at: datetime
    expires_at: datetime
    current: bool = False
