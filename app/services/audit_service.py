import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_audit_log import DocumentAuditLog


async def create_document_audit_log(
    db: AsyncSession,
    document_id: uuid.UUID,
    action: str,
    message: str | None = None,
    actor_user_id: uuid.UUID | None = None,
    extra_data: dict[str, Any] | None = None,
) -> DocumentAuditLog:
    audit_log = DocumentAuditLog(
        document_id=document_id,
        actor_user_id=actor_user_id,
        action=action,
        message=message,
        extra_data=extra_data,
    )

    db.add(audit_log)

    return audit_log