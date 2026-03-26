from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from domain.enums import UserRole, UserStatus


class UserOut(BaseModel):
    id: int
    telegram_user_id: int
    full_name: Optional[str]
    username: Optional[str]
    role: UserRole
    status: UserStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    telegram_user_id: int
    full_name: Optional[str] = None
    username: Optional[str] = None
    role: UserRole = UserRole.VIEWER
