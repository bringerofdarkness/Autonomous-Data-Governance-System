from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_roles
from app.db.session import get_db_session
from app.models.document_audit_log import DocumentAuditLog
from app.models.document_metadata import DocumentStatus
from app.models.rag_search_audit_log import RagSearchAuditLog
from app.models.user import User

from app.services.audit_service import create_document_audit_log
from app.services.qdrant_service import check_qdrant_health, ensure_gold_collection
from app.models.document_metadata import DocumentMetadata
from app.services.qdrant_service import (
    check_qdrant_health,
    ensure_gold_collection,
    get_gold_collection_chunks_for_document,
    get_gold_collection_point,
)

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


@router.get("/qdrant-integrity")
async def check_qdrant_integrity(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles(["Admin"])),
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
        description="Maximum number of indexed documents to check.",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of indexed documents to skip.",
    ),
) -> dict:
    indexed_documents_result = await db.execute(
        select(DocumentMetadata)
        .where(DocumentMetadata.qdrant_point_id.is_not(None))
        .order_by(DocumentMetadata.indexed_at.desc())
        .limit(limit)
        .offset(offset)
    )

    indexed_documents = indexed_documents_result.scalars().all()

    integrity_items = []
    ok_count = 0
    broken_count = 0

    for document in indexed_documents:
        qdrant_point_result = get_gold_collection_point(
            point_id=str(document.qdrant_point_id)
        )

        qdrant_chunks = get_gold_collection_chunks_for_document(
            document_id=str(document.id),
            limit=200,
        )

        document_point_found = qdrant_point_result["found"]
        chunk_points_count = len(qdrant_chunks)

        integrity_status = (
            "OK"
            if document_point_found and chunk_points_count > 0
            else "BROKEN"
        )

        if integrity_status == "OK":
            ok_count += 1
        else:
            broken_count += 1

        integrity_items.append(
            {
                "document_id": str(document.id),
                "original_filename": document.original_filename,
                "status": document.status.value,
                "document_category": document.document_category,
                "risk_score": document.risk_score,
                "qdrant_point_id": str(document.qdrant_point_id)
                if document.qdrant_point_id
                else None,
                "indexed_at": document.indexed_at.isoformat()
                if document.indexed_at
                else None,
                "document_point_found": document_point_found,
                "chunk_points_count": chunk_points_count,
                "integrity_status": integrity_status,
            }
        )

    return {
        "checked_count": len(integrity_items),
        "ok_count": ok_count,
        "broken_count": broken_count,
        "items": integrity_items,
    }

@router.post("/qdrant-integrity/repair")
async def repair_qdrant_integrity(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles(["Admin"])),
    dry_run: bool = Query(
        default=True,
        description="If true, only report broken records without modifying PostgreSQL.",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
        description="Maximum number of indexed documents to inspect.",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of indexed documents to skip.",
    ),
) -> dict:
    indexed_documents_result = await db.execute(
        select(DocumentMetadata)
        .where(DocumentMetadata.qdrant_point_id.is_not(None))
        .order_by(DocumentMetadata.indexed_at.desc())
        .limit(limit)
        .offset(offset)
    )

    indexed_documents = indexed_documents_result.scalars().all()

    checked_count = 0
    broken_count = 0
    repaired_count = 0
    broken_items = []

    for document in indexed_documents:
        checked_count += 1

        qdrant_point_result = get_gold_collection_point(
            point_id=str(document.qdrant_point_id)
        )

        qdrant_chunks = get_gold_collection_chunks_for_document(
            document_id=str(document.id),
            limit=200,
        )

        document_point_found = qdrant_point_result["found"]
        chunk_points_count = len(qdrant_chunks)

        is_broken = not document_point_found or chunk_points_count == 0

        if not is_broken:
            continue

        broken_count += 1

        broken_item = {
            "document_id": str(document.id),
            "original_filename": document.original_filename,
            "status": document.status.value,
            "document_category": document.document_category,
            "risk_score": document.risk_score,
            "old_qdrant_point_id": str(document.qdrant_point_id)
            if document.qdrant_point_id
            else None,
            "old_indexed_at": document.indexed_at.isoformat()
            if document.indexed_at
            else None,
            "document_point_found": document_point_found,
            "chunk_points_count": chunk_points_count,
            "repair_action": (
                "DRY_RUN_ONLY"
                if dry_run
                else "CLEARED_POSTGRES_QDRANT_INDEX_FIELDS"
            ),
        }

        broken_items.append(broken_item)

        if dry_run:
            continue

        old_qdrant_point_id = document.qdrant_point_id
        old_indexed_at = document.indexed_at

        document.qdrant_point_id = None
        document.indexed_at = None

        await create_document_audit_log(
            db=db,
            document_id=document.id,
            actor_user_id=current_user.id,
            action="DOCUMENT_QDRANT_INTEGRITY_REPAIRED",
            message=(
                "Stale PostgreSQL Qdrant indexing fields were cleared "
                f"by {current_user.email} after integrity check."
            ),
            extra_data={
                "repaired_by": current_user.email,
                "old_qdrant_point_id": str(old_qdrant_point_id)
                if old_qdrant_point_id
                else None,
                "old_indexed_at": old_indexed_at.isoformat()
                if old_indexed_at
                else None,
                "document_point_found": document_point_found,
                "chunk_points_count": chunk_points_count,
            },
        )

        repaired_count += 1

    if not dry_run:
        await db.commit()

    return {
        "dry_run": dry_run,
        "checked_count": checked_count,
        "broken_count": broken_count,
        "repaired_count": repaired_count,
        "items": broken_items,
    }