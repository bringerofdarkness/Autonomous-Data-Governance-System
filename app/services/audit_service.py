import uuid
from typing import Any

from app.models import DocumentAuditLog


def create_document_audit_log(
    document_id: uuid.UUID,
    action: str,
    message: str | None = None,
    actor_user_id: uuid.UUID | None = None,
    extra_data: dict[str, Any] | None = None,
) -> DocumentAuditLog:
    # Use synchronous Django ORM creation
    audit_log = DocumentAuditLog.objects.create(
        document_id=document_id,
        actor_user_id=actor_user_id,
        action=action,
        message=message,
        extra_data=extra_data,
    )

    return audit_log