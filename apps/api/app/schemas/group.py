from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.user import UserRead


class GroupCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)


class GroupInvite(BaseModel):
    username: str


class GroupRead(BaseModel):
    id: UUID
    name: str
    owner_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GroupDetail(GroupRead):
    members: list[UserRead]

