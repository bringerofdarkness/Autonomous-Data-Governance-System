from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_roles
from app.db.session import get_db_session
from app.models.document_audit_log import DocumentAuditLog
from app.models.document_metadata import DocumentMetadata, DocumentStatus
from app.models.rag_search_audit_log import RagSearchAuditLog
from app.models.user import User
from app.services.qdrant_service import check_qdrant_health, ensure_gold_collection


router = APIRouter(prefix="/system", tags=["System"])


@router.get("/qdrant-health")
async def qdrant_health(
    current_user: User = Depends(require_roles(["Admin"])),
) -> dict[str, str]:
    try:
        return check_qdrant_health()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Qdrant is not reachable: {exc}",
        )


@router.post("/qdrant/gold-collection")
async def create_gold_collection(
    current_user: User = Depends(require_roles(["Admin"])),
) -> dict[str, str]:
    try:
        return ensure_gold_collection()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not create Qdrant gold collection: {exc}",
        )


@router.get("/audit-summary")
async def get_system_audit_summary(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles(["Admin"])),
) -> dict:
    now = datetime.now(timezone.utc)
    last_24h = now - timedelta(hours=24)

    status_counts_result = await db.execute(
        select(
            DocumentMetadata.status,
            func.count(DocumentMetadata.id),
        )
        .group_by(DocumentMetadata.status)
    )

    status_counts = {
        status.value: count
        for status, count in status_counts_result.all()
    }

    total_documents = sum(status_counts.values())

    indexed_documents_result = await db.execute(
        select(func.count(DocumentMetadata.id)).where(
            DocumentMetadata.qdrant_point_id.is_not(None)
        )
    )
    indexed_documents = indexed_documents_result.scalar_one()

    conflict_found_result = await db.execute(
        select(func.count(DocumentMetadata.id)).where(
            DocumentMetadata.conflict_found.is_(True)
        )
    )
    conflict_found_count = conflict_found_result.scalar_one()

    high_risk_documents_result = await db.execute(
        select(func.count(DocumentMetadata.id)).where(
            DocumentMetadata.risk_score >= 75
        )
    )
    high_risk_documents = high_risk_documents_result.scalar_one()

    recent_documents_result = await db.execute(
        select(func.count(DocumentMetadata.id)).where(
            DocumentMetadata.created_at >= last_24h
        )
    )
    recent_documents_24h = recent_documents_result.scalar_one()

    total_rag_searches_result = await db.execute(
        select(func.count(RagSearchAuditLog.id))
    )
    total_rag_searches = total_rag_searches_result.scalar_one()

    recent_rag_searches_result = await db.execute(
        select(func.count(RagSearchAuditLog.id)).where(
            RagSearchAuditLog.created_at >= last_24h
        )
    )
    recent_rag_searches_24h = recent_rag_searches_result.scalar_one()

    total_document_audit_logs_result = await db.execute(
        select(func.count(DocumentAuditLog.id))
    )
    total_document_audit_logs = total_document_audit_logs_result.scalar_one()

    recent_document_audit_logs_result = await db.execute(
        select(func.count(DocumentAuditLog.id)).where(
            DocumentAuditLog.created_at >= last_24h
        )
    )
    recent_document_audit_logs_24h = recent_document_audit_logs_result.scalar_one()

    return {
        "generated_at": now.isoformat(),
        "documents": {
            "total": total_documents,
            "uploaded": status_counts.get(DocumentStatus.UPLOADED.value, 0),
            "processing": status_counts.get(DocumentStatus.PROCESSING.value, 0),
            "paused": status_counts.get(DocumentStatus.PAUSED.value, 0),
            "waiting_for_admin": status_counts.get(
                DocumentStatus.WAITING_FOR_ADMIN.value,
                0,
            ),
            "approved": status_counts.get(DocumentStatus.APPROVED.value, 0),
            "rejected": status_counts.get(DocumentStatus.REJECTED.value, 0),
            "failed": status_counts.get(DocumentStatus.FAILED.value, 0),
            "indexed": indexed_documents,
            "conflict_found": conflict_found_count,
            "high_risk": high_risk_documents,
            "created_last_24h": recent_documents_24h,
        },
        "rag": {
            "total_searches": total_rag_searches,
            "searches_last_24h": recent_rag_searches_24h,
        },
        "audit_logs": {
            "document_audit_logs_total": total_document_audit_logs,
            "document_audit_logs_last_24h": recent_document_audit_logs_24h,
        },
    }