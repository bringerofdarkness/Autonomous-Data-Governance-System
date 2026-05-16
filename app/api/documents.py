import uuid
from typing import Any

from langgraph.types import Command

from app.graph.workflow import build_adgs_graph

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_audit_log import DocumentAuditLog
from app.schemas.audit import DocumentAuditLogResponse

from app.services.conflict_service import check_document_conflicts

from app.services.qdrant_service import (
    get_gold_collection_chunks_for_document,
    get_gold_collection_point,
)
from app.services.document_indexing_service import index_cleaned_document_in_qdrant
from app.api.dependencies import require_roles
from app.db.session import get_db_session
from app.models.document_metadata import DocumentMetadata, DocumentStatus
from app.models.user import User
from app.schemas.document import (
    ConflictMatchResponse,
    DocumentConflictCheckResponse,
    DocumentDecisionRequest,
    DocumentDecisionResponse,
    DocumentIndexResponse,
    DocumentListItemResponse,
    DocumentQdrantPointResponse,
    DocumentReprocessResponse,
    DocumentResumeRequest,
    DocumentResumeResponse,
    DocumentStatusResponse,
    DocumentSummaryResponse,
    DocumentTaskStatusResponse,
    DocumentUploadResponse,
    DocumentQdrantChunksResponse,
    QdrantChunkResponse,
)
from app.services.audit_service import create_document_audit_log
from app.services.document_service import save_uploaded_document
from app.workers.celery_app import celery_app
from app.workers.tasks import process_document_task


router = APIRouter(prefix="/documents", tags=["Documents"])


def make_json_safe(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, dict):
        return {
            str(key): make_json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [make_json_safe(item) for item in value]

    return str(value)

@router.get(
    "/summary",
    response_model=DocumentSummaryResponse,
)
async def get_documents_summary(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles(["Admin", "Editor", "Viewer"])),
) -> DocumentSummaryResponse:
    result = await db.execute(
        select(
            DocumentMetadata.status,
            func.count(DocumentMetadata.id),
        )
        .group_by(DocumentMetadata.status)
    )

    status_counts = {
        status.value: count
        for status, count in result.all()
    }

    total = sum(status_counts.values())
    conflict_count_result = await db.execute(
        select(func.count(DocumentMetadata.id)).where(
            DocumentMetadata.conflict_found.is_(True)
        )
    )
    conflict_found_count = conflict_count_result.scalar_one()

    indexed_count_result = await db.execute(
        select(func.count(DocumentMetadata.id)).where(
            DocumentMetadata.qdrant_point_id.is_not(None)
        )
    )
    indexed_count = indexed_count_result.scalar_one()

    waiting_conflict_result = await db.execute(
        select(func.count(DocumentMetadata.id)).where(
            DocumentMetadata.status == DocumentStatus.WAITING_FOR_ADMIN,
            DocumentMetadata.conflict_found.is_(True),
        )
    )
    waiting_for_admin_with_conflict = waiting_conflict_result.scalar_one()

    return DocumentSummaryResponse(
        total=total,
        uploaded=status_counts.get(DocumentStatus.UPLOADED.value, 0),
        processing=status_counts.get(DocumentStatus.PROCESSING.value, 0),
        waiting_for_admin=status_counts.get(
            DocumentStatus.WAITING_FOR_ADMIN.value,
            0,
        ),
        approved=status_counts.get(DocumentStatus.APPROVED.value, 0),
        rejected=status_counts.get(DocumentStatus.REJECTED.value, 0),
        failed=status_counts.get(DocumentStatus.FAILED.value, 0),
        conflict_found_count=conflict_found_count,
        indexed_count=indexed_count,
        waiting_for_admin_with_conflict=waiting_for_admin_with_conflict,
    )


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles(["Admin", "Editor"])),
) -> DocumentUploadResponse:
    document = await save_uploaded_document(
        db=db,
        file=file,
        uploaded_by=current_user,
    )

    task = process_document_task.delay(str(document.id))

    document.celery_task_id = task.id

    await create_document_audit_log(
        db=db,
        document_id=document.id,
        actor_user_id=current_user.id,
        action="DOCUMENT_UPLOADED",
        message=f"Document uploaded by {current_user.email}. Background processing started.",
        extra_data={
            "original_filename": document.original_filename,
            "stored_filename": document.stored_filename,
            "content_type": document.content_type,
            "file_size_bytes": document.file_size_bytes,
            "celery_task_id": task.id,
        },
    )

    await db.commit()
    await db.refresh(document)

    return DocumentUploadResponse.model_validate(document)


@router.get(
    "/{document_id}/status",
    response_model=DocumentStatusResponse,
)
async def get_document_status(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles(["Admin", "Editor", "Viewer"])),
) -> DocumentStatusResponse:
    result = await db.execute(
        select(DocumentMetadata).where(DocumentMetadata.id == document_id)
    )
    document = result.scalar_one_or_none()

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    return DocumentStatusResponse.model_validate(document)


@router.get(
    "/{document_id}/task-status",
    response_model=DocumentTaskStatusResponse,
)
async def get_document_task_status(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles(["Admin", "Editor", "Viewer"])),
) -> DocumentTaskStatusResponse:
    result = await db.execute(
        select(DocumentMetadata).where(DocumentMetadata.id == document_id)
    )
    document = result.scalar_one_or_none()

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    celery_state = None
    celery_result = None

    if document.celery_task_id:
        task_result = celery_app.AsyncResult(document.celery_task_id)
        celery_state = task_result.state

        if task_result.ready():
            celery_result = make_json_safe(task_result.result)

    return DocumentTaskStatusResponse(
        document_id=document.id,
        original_filename=document.original_filename,
        database_status=document.status,
        document_category=document.document_category,
        risk_score=document.risk_score,
        celery_task_id=document.celery_task_id,
        celery_state=celery_state,
        celery_result=celery_result,
        error_message=document.error_message,
    )

@router.post(
    "/{document_id}/reprocess",
    response_model=DocumentReprocessResponse,
)
async def reprocess_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles(["Admin", "Editor"])),
) -> DocumentReprocessResponse:
    result = await db.execute(
        select(DocumentMetadata).where(DocumentMetadata.id == document_id)
    )
    document = result.scalar_one_or_none()

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    allowed_statuses = {
        DocumentStatus.UPLOADED,
        DocumentStatus.FAILED,
    }

    is_legacy_conflict_waiting_document = (
        document.status == DocumentStatus.WAITING_FOR_ADMIN
        and document.conflict_found is True
    )

    if document.status not in allowed_statuses and not is_legacy_conflict_waiting_document:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Only UPLOADED, FAILED, or legacy WAITING_FOR_ADMIN conflict "
                "documents can be reprocessed."
            ),
        )

    previous_status = document.status

    task = process_document_task.delay(str(document.id))

    document.celery_task_id = task.id
    document.status = DocumentStatus.UPLOADED
    document.error_message = None
    document.conflict_found = False
    document.conflict_summary = None
    document.conflict_checked_at = None

    await create_document_audit_log(
        db=db,
        document_id=document.id,
        actor_user_id=current_user.id,
        action="DOCUMENT_REPROCESS_REQUESTED",
        message=f"Document reprocessing requested by {current_user.email}.",
        extra_data={
            "celery_task_id": task.id,
            "requested_by": current_user.email,
            "previous_status": previous_status.value,
        },
    )

    await db.commit()
    await db.refresh(document)

    return DocumentReprocessResponse(
        id=document.id,
        original_filename=document.original_filename,
        status=document.status,
        celery_task_id=task.id,
        message="Document reprocessing started.",
    )

@router.post(
    "/{document_id}/index",
    response_model=DocumentIndexResponse,
)
async def index_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles(["Admin"])),
) -> DocumentIndexResponse:
    result = await db.execute(
        select(DocumentMetadata).where(DocumentMetadata.id == document_id)
    )
    document = result.scalar_one_or_none()

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    if document.status != DocumentStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only APPROVED documents can be indexed into Qdrant.",
        )

    if not document.cleaned_text_filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document has no cleaned text file. Reprocess the document first.",
        )
    if document.conflict_found:
        hitl_result = await db.execute(
            select(DocumentAuditLog).where(
                DocumentAuditLog.document_id == document.id,
                DocumentAuditLog.action == "DOCUMENT_HITL_APPROVED",
            )
        )
        hitl_approval_log = hitl_result.scalar_one_or_none()

        if hitl_approval_log is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "This document has a detected conflict. "
                    "It can only be indexed after HITL approval through the resume API."
                ),
            )

    indexing_result = index_cleaned_document_in_qdrant(
        document_id=document.id,
        original_filename=document.original_filename,
        cleaned_text_filename=document.cleaned_text_filename,
        document_category=document.document_category,
        risk_score=document.risk_score,
    )

    document.qdrant_point_id = indexing_result["qdrant_point_id"]
    document.indexed_at = datetime.now(timezone.utc)

    await create_document_audit_log(
        db=db,
        document_id=document.id,
        actor_user_id=current_user.id,
        action="DOCUMENT_INDEXED_IN_QDRANT",
        message=f"Document indexed into Qdrant Gold collection by {current_user.email}.",
        extra_data={
            "qdrant_point_id": str(document.qdrant_point_id),
            "collection_name": indexing_result["collection_name"],
            "vector_size": indexing_result["vector_size"],
            "chunks_indexed": indexing_result["chunks_indexed"],
            "points_indexed": indexing_result["points_indexed"],
            "indexed_by": current_user.email,
        },
    )

    await db.commit()
    await db.refresh(document)

    return DocumentIndexResponse(
        id=document.id,
        original_filename=document.original_filename,
        status=document.status,
        document_category=document.document_category,
        risk_score=document.risk_score,
        qdrant_point_id=document.qdrant_point_id,
        indexed_at=document.indexed_at,
        chunks_indexed=indexing_result["chunks_indexed"],
        points_indexed=indexing_result["points_indexed"],
        message="Document indexed into Qdrant Gold collection successfully.",
    )

@router.get(
    "/{document_id}/qdrant-point",
    response_model=DocumentQdrantPointResponse,
)
async def get_document_qdrant_point(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles(["Admin"])),
) -> DocumentQdrantPointResponse:
    result = await db.execute(
        select(DocumentMetadata).where(DocumentMetadata.id == document_id)
    )
    document = result.scalar_one_or_none()

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    if not document.qdrant_point_id:
        return DocumentQdrantPointResponse(
            document_id=document.id,
            original_filename=document.original_filename,
            indexed=False,
            qdrant_point_id=None,
            collection_name=None,
            payload=None,
            message="Document has not been indexed into Qdrant yet.",
        )

    qdrant_result = get_gold_collection_point(
        point_id=str(document.qdrant_point_id)
    )

    return DocumentQdrantPointResponse(
        document_id=document.id,
        original_filename=document.original_filename,
        indexed=qdrant_result["found"],
        qdrant_point_id=document.qdrant_point_id,
        collection_name=qdrant_result["collection_name"],
        payload=qdrant_result["payload"],
        message=(
            "Document point exists in Qdrant Gold collection."
            if qdrant_result["found"]
            else "Document has qdrant_point_id in PostgreSQL, but point was not found in Qdrant."
        ),
    )


@router.get(
    "/{document_id}/qdrant-chunks",
    response_model=DocumentQdrantChunksResponse,
)
async def get_document_qdrant_chunks(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles(["Admin"])),
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
        description="Maximum number of Qdrant chunk points to return.",
    ),
) -> DocumentQdrantChunksResponse:
    result = await db.execute(
        select(DocumentMetadata).where(DocumentMetadata.id == document_id)
    )
    document = result.scalar_one_or_none()

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    if not document.qdrant_point_id:
        return DocumentQdrantChunksResponse(
            document_id=document.id,
            original_filename=document.original_filename,
            indexed=False,
            chunks_count=0,
            chunks=[],
            message="Document has not been indexed into Qdrant yet.",
        )

    qdrant_chunks = get_gold_collection_chunks_for_document(
        document_id=str(document.id),
        limit=limit,
    )

    chunks = [
        QdrantChunkResponse(
            point_id=chunk["point_id"],
            chunk_index=chunk["payload"].get("chunk_index")
            if chunk.get("payload")
            else None,
            chunk_text=chunk["payload"].get("chunk_text")
            if chunk.get("payload")
            else None,
            char_count=chunk["payload"].get("char_count")
            if chunk.get("payload")
            else None,
            payload=chunk["payload"],
        )
        for chunk in qdrant_chunks
    ]

    return DocumentQdrantChunksResponse(
        document_id=document.id,
        original_filename=document.original_filename,
        indexed=True,
        chunks_count=len(chunks),
        chunks=chunks,
        message="Qdrant chunk points retrieved successfully.",
    )


@router.post(
    "/{document_id}/conflict-check",
    response_model=DocumentConflictCheckResponse,
)
async def conflict_check_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles(["Admin", "Editor"])),
    similarity_threshold: float = Query(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score required to mark a match as a potential conflict.",
    ),
    limit: int = Query(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of Qdrant matches to check.",
    ),
) -> DocumentConflictCheckResponse:
    result = await db.execute(
        select(DocumentMetadata).where(DocumentMetadata.id == document_id)
    )
    document = result.scalar_one_or_none()

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    if not document.cleaned_text_filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document has no cleaned text file. Reprocess the document first.",
        )

    conflict_result = check_document_conflicts(
        document_id=document.id,
        cleaned_text_filename=document.cleaned_text_filename,
        similarity_threshold=similarity_threshold,
        limit=limit,
    )

    potential_conflicts = conflict_result["potential_conflicts"]

    if conflict_result["conflict_found"]:
        top_match = potential_conflicts[0]
        document.conflict_summary = (
            f"Potential conflict found with Qdrant point "
            f"{top_match['point_id']} at similarity score {top_match['score']:.4f}."
        )
    else:
        document.conflict_summary = (
            "No potential conflict found in Qdrant Gold collection."
        )

    document.conflict_found = conflict_result["conflict_found"]
    document.conflict_checked_at = datetime.now(timezone.utc)

    await create_document_audit_log(
        db=db,
        document_id=document.id,
        actor_user_id=current_user.id,
        action="DOCUMENT_CONFLICT_CHECKED",
        message=(
            "Potential conflict found in Qdrant Gold collection."
            if conflict_result["conflict_found"]
            else "No potential conflict found in Qdrant Gold collection."
        ),
        extra_data={
            "similarity_threshold": similarity_threshold,
            "matches_checked": conflict_result["matches_checked"],
            "conflict_found": conflict_result["conflict_found"],
            "conflict_summary": document.conflict_summary,
            "checked_by": current_user.email,
            "potential_conflicts": [
                {
                    "point_id": match["point_id"],
                    "score": match["score"],
                    "original_filename": (
                        match["payload"].get("original_filename")
                        if match.get("payload")
                        else None
                    ),
                    "document_category": (
                        match["payload"].get("document_category")
                        if match.get("payload")
                        else None
                    ),
                }
                for match in potential_conflicts
            ],
        },
    )

    await db.commit()

    return DocumentConflictCheckResponse(
        document_id=document.id,
        original_filename=document.original_filename,
        conflict_found=conflict_result["conflict_found"],
        similarity_threshold=conflict_result["similarity_threshold"],
        matches_checked=conflict_result["matches_checked"],
        potential_conflicts=[
            ConflictMatchResponse(
                point_id=match["point_id"],
                score=match["score"],
                payload=match["payload"],
            )
            for match in potential_conflicts
        ],
        message=(
            "Potential conflict found."
            if conflict_result["conflict_found"]
            else "No potential conflict found."
        ),
    )

@router.post(
    "/{document_id}/resume",
    response_model=DocumentResumeResponse,
)
async def resume_paused_document_workflow(
    document_id: uuid.UUID,
    resume_request: DocumentResumeRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles(["Admin"])),
) -> DocumentResumeResponse:
    result = await db.execute(
        select(DocumentMetadata).where(DocumentMetadata.id == document_id)
    )
    document = result.scalar_one_or_none()

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    allowed_resume_statuses = {
        DocumentStatus.PAUSED,
        DocumentStatus.WAITING_FOR_ADMIN,
    }

    if document.status not in allowed_resume_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only documents waiting for Admin review can be resumed.",
        )

    graph = build_adgs_graph()

    graph_config = {
        "configurable": {
            "thread_id": f"document:{document.id}",
        }
    }

    graph_result = graph.invoke(
        Command(
            resume={
                "decision": resume_request.decision,
                "reason": resume_request.reason,
            }
        ),
        config=graph_config,
    )

    if graph_result.get("current_step") == "FAILED":
        document.status = DocumentStatus.FAILED
        document.error_message = graph_result.get(
            "error_message",
            "HITL resume failed.",
        )

        await create_document_audit_log(
            db=db,
            document_id=document.id,
            actor_user_id=current_user.id,
            action="DOCUMENT_HITL_RESUME_FAILED",
            message=document.error_message,
            extra_data={
                "thread_id": f"document:{document.id}",
                "resumed_by": current_user.email,
                "decision": resume_request.decision,
            },
        )

        await db.commit()
        await db.refresh(document)

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=document.error_message,
        )

    hitl_decision = graph_result.get("hitl_decision") or resume_request.decision
    hitl_reason = graph_result.get("hitl_reason") or resume_request.reason

    if hitl_decision == "approve":
        document.status = DocumentStatus.APPROVED
        document.error_message = hitl_reason
        audit_action = "DOCUMENT_HITL_APPROVED"
        response_message = "Paused workflow resumed and document approved."
    elif hitl_decision == "reject":
        document.status = DocumentStatus.REJECTED
        document.error_message = hitl_reason
        audit_action = "DOCUMENT_HITL_REJECTED"
        response_message = "Paused workflow resumed and document rejected."
    else:
        document.status = DocumentStatus.FAILED
        document.error_message = "Invalid HITL decision returned by graph."
        audit_action = "DOCUMENT_HITL_RESUME_FAILED"
        response_message = document.error_message

    await create_document_audit_log(
        db=db,
        document_id=document.id,
        actor_user_id=current_user.id,
        action=audit_action,
        message=hitl_reason,
        extra_data={
            "thread_id": f"document:{document.id}",
            "resumed_by": current_user.email,
            "hitl_decision": hitl_decision,
            "conflict_found": document.conflict_found,
            "conflict_summary": document.conflict_summary,
            "risk_score": document.risk_score,
            "document_category": document.document_category,
        },
    )

    if hitl_decision == "approve":
        if not document.cleaned_text_filename:
            document.status = DocumentStatus.FAILED
            document.error_message = (
                "Document was approved, but indexing failed because cleaned text is missing."
            )

            await create_document_audit_log(
                db=db,
                document_id=document.id,
                actor_user_id=current_user.id,
                action="DOCUMENT_INDEXING_FAILED",
                message=document.error_message,
                extra_data={
                    "reason": "missing_cleaned_text_filename",
                    "approved_by": current_user.email,
                    "indexing_trigger": "HITL_APPROVAL_RESUME",
                },
            )

            await db.commit()
            await db.refresh(document)

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=document.error_message,
            )

        try:
            indexing_result = index_cleaned_document_in_qdrant(
                document_id=document.id,
                original_filename=document.original_filename,
                cleaned_text_filename=document.cleaned_text_filename,
                document_category=document.document_category,
                risk_score=document.risk_score,
            )
        except Exception as exc:
            document.status = DocumentStatus.FAILED
            document.error_message = (
                "Document was approved, but automatic Qdrant indexing failed."
            )

            await create_document_audit_log(
                db=db,
                document_id=document.id,
                actor_user_id=current_user.id,
                action="DOCUMENT_INDEXING_FAILED",
                message=document.error_message,
                extra_data={
                    "reason": str(exc),
                    "approved_by": current_user.email,
                    "indexing_trigger": "HITL_APPROVAL_RESUME",
                },
            )

            await db.commit()
            await db.refresh(document)

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=document.error_message,
            )

        document.qdrant_point_id = indexing_result["qdrant_point_id"]
        document.indexed_at = datetime.now(timezone.utc)

        response_message = (
            "Paused workflow resumed, document approved, and indexed into Qdrant Gold collection."
        )

        await create_document_audit_log(
            db=db,
            document_id=document.id,
            actor_user_id=current_user.id,
            action="DOCUMENT_INDEXED_IN_QDRANT",
            message=(
                "Document automatically indexed into Qdrant Gold collection "
                f"after Admin approval by {current_user.email}."
            ),
            extra_data={
                "qdrant_point_id": str(document.qdrant_point_id),
                "collection_name": indexing_result["collection_name"],
                "vector_size": indexing_result["vector_size"],
                "chunks_indexed": indexing_result["chunks_indexed"],
                "points_indexed": indexing_result["points_indexed"],
                "indexed_by": current_user.email,
                "indexing_trigger": "HITL_APPROVAL_RESUME",
            },
        )

    await db.commit()
    await db.refresh(document)

    return DocumentResumeResponse(
        id=document.id,
        original_filename=document.original_filename,
        status=document.status,
        hitl_decision=hitl_decision,
        hitl_reason=hitl_reason,
        message=response_message,
    )


@router.post(
    "/{document_id}/approve",
    response_model=DocumentDecisionResponse,
)
async def approve_document(
    document_id: uuid.UUID,
    decision: DocumentDecisionRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles(["Admin"])),
) -> DocumentDecisionResponse:
    result = await db.execute(
        select(DocumentMetadata).where(DocumentMetadata.id == document_id)
    )
    document = result.scalar_one_or_none()

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    if document.status != DocumentStatus.WAITING_FOR_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only documents waiting for admin approval can be approved.",
        )
    if document.conflict_found:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "This document has a detected conflict. "
                "Use the HITL resume endpoint to approve or reject it."
            ),
        )

    old_status = document.status
    decision_message = (
        decision.reason
        or f"Approved by admin: {current_user.email}"
    )

    document.status = DocumentStatus.APPROVED
    document.error_message = decision_message

    await create_document_audit_log(
        db=db,
        document_id=document.id,
        actor_user_id=current_user.id,
        action="DOCUMENT_APPROVED",
        message=decision_message,
        extra_data={
            "old_status": old_status.value,
            "new_status": DocumentStatus.APPROVED.value,
            "approved_by": current_user.email,
            "document_category": document.document_category,
            "risk_score": document.risk_score,
        },
    )

    await db.commit()
    await db.refresh(document)

    return DocumentDecisionResponse(
        id=document.id,
        original_filename=document.original_filename,
        status=document.status,
        document_category=document.document_category,
        risk_score=document.risk_score,
        decision_message=decision_message,
    )


@router.post(
    "/{document_id}/reject",
    response_model=DocumentDecisionResponse,
)
async def reject_document(
    document_id: uuid.UUID,
    decision: DocumentDecisionRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles(["Admin"])),
) -> DocumentDecisionResponse:
    result = await db.execute(
        select(DocumentMetadata).where(DocumentMetadata.id == document_id)
    )
    document = result.scalar_one_or_none()

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    if document.status != DocumentStatus.WAITING_FOR_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only documents waiting for admin approval can be rejected.",
        )

    old_status = document.status
    decision_message = (
        decision.reason
        or f"Rejected by admin: {current_user.email}"
    )

    document.status = DocumentStatus.REJECTED
    document.error_message = decision_message

    await create_document_audit_log(
        db=db,
        document_id=document.id,
        actor_user_id=current_user.id,
        action="DOCUMENT_REJECTED",
        message=decision_message,
        extra_data={
            "old_status": old_status.value,
            "new_status": DocumentStatus.REJECTED.value,
            "rejected_by": current_user.email,
            "document_category": document.document_category,
            "risk_score": document.risk_score,
        },
    )

    await db.commit()
    await db.refresh(document)

    return DocumentDecisionResponse(
        id=document.id,
        original_filename=document.original_filename,
        status=document.status,
        document_category=document.document_category,
        risk_score=document.risk_score,
        decision_message=decision_message,
    )

@router.get(
    "/{document_id}/audit-logs",
    response_model=list[DocumentAuditLogResponse],
)
async def get_document_audit_logs(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles(["Admin", "Editor", "Viewer"])),
    action: str | None = Query(
        default=None,
        min_length=1,
        max_length=100,
        description="Filter document audit logs by action.",
    ),
    actor_user_id: uuid.UUID | None = Query(
        default=None,
        description="Filter document audit logs by actor user ID.",
    ),
    date_from: datetime | None = Query(
        default=None,
        description="Return logs created at or after this datetime.",
    ),
    date_to: datetime | None = Query(
        default=None,
        description="Return logs created at or before this datetime.",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
        description="Maximum number of document audit logs to return.",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of document audit logs to skip.",
    ),
) -> list[DocumentAuditLogResponse]:
    document_result = await db.execute(
        select(DocumentMetadata).where(DocumentMetadata.id == document_id)
    )
    document = document_result.scalar_one_or_none()

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    query_stmt = select(DocumentAuditLog).where(
        DocumentAuditLog.document_id == document_id
    )

    if action:
        query_stmt = query_stmt.where(
            DocumentAuditLog.action == action.strip()
        )

    if actor_user_id is not None:
        query_stmt = query_stmt.where(
            DocumentAuditLog.actor_user_id == actor_user_id
        )

    if date_from is not None:
        query_stmt = query_stmt.where(
            DocumentAuditLog.created_at >= date_from
        )

    if date_to is not None:
        query_stmt = query_stmt.where(
            DocumentAuditLog.created_at <= date_to
        )

    query_stmt = (
        query_stmt
        .order_by(DocumentAuditLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    logs_result = await db.execute(query_stmt)
    audit_logs = logs_result.scalars().all()

    return [
        DocumentAuditLogResponse.model_validate(log)
        for log in audit_logs
    ]



@router.get(
    "",
    response_model=list[DocumentListItemResponse],
)
async def list_documents(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles(["Admin", "Editor", "Viewer"])),
    document_status: DocumentStatus | None = Query(
        default=None,
        alias="status",
        description="Filter documents by processing status.",
    ),
    document_category: str | None = Query(
        default=None,
        description="Filter documents by detected category.",
    ),
    min_risk_score: int | None = Query(
        default=None,
        ge=0,
        le=100,
        description="Return documents with risk score greater than or equal to this value.",
    ),
    max_risk_score: int | None = Query(
        default=None,
        ge=0,
        le=100,
        description="Return documents with risk score less than or equal to this value.",
    ),
    conflict_found: bool | None = Query(
        default=None,
        description="Filter documents by whether a conflict was found.",
    ),
    indexed: bool | None = Query(
        default=None,
        description="Filter documents by whether they were indexed into Qdrant.",
    ),
    uploaded_by_id: uuid.UUID | None = Query(
        default=None,
        description="Filter documents by uploader user ID.",
    ),
    created_from: datetime | None = Query(
        default=None,
        description="Return documents created at or after this datetime.",
    ),
    created_to: datetime | None = Query(
        default=None,
        description="Return documents created at or before this datetime.",
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of documents to return.",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of documents to skip.",
    ),
) -> list[DocumentListItemResponse]:
    query = select(DocumentMetadata)

    if document_status is not None:
        query = query.where(DocumentMetadata.status == document_status)

    if document_category is not None:
        query = query.where(
            DocumentMetadata.document_category == document_category.strip()
        )

    if min_risk_score is not None:
        query = query.where(DocumentMetadata.risk_score >= min_risk_score)

    if max_risk_score is not None:
        query = query.where(DocumentMetadata.risk_score <= max_risk_score)

    if conflict_found is not None:
        query = query.where(DocumentMetadata.conflict_found.is_(conflict_found))

    if indexed is True:
        query = query.where(DocumentMetadata.qdrant_point_id.is_not(None))

    if indexed is False:
        query = query.where(DocumentMetadata.qdrant_point_id.is_(None))

    if uploaded_by_id is not None:
        query = query.where(DocumentMetadata.uploaded_by_id == uploaded_by_id)

    if created_from is not None:
        query = query.where(DocumentMetadata.created_at >= created_from)

    if created_to is not None:
        query = query.where(DocumentMetadata.created_at <= created_to)

    query = (
        query
        .order_by(DocumentMetadata.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    result = await db.execute(query)
    documents = result.scalars().all()

    return [
        DocumentListItemResponse.model_validate(document)
        for document in documents
    ]

