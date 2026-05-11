import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class DocumentAuditLogResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    actor_user_id: uuid.UUID | None
    action: str
    message: str | None
    extra_data: dict[str, Any] | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)