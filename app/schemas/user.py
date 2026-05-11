import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class RoleResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None

    model_config = ConfigDict(from_attributes=True)


class CurrentUserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    is_active: bool
    roles: list[RoleResponse]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)