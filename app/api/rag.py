
import uuid
from datetime import datetime



from fastapi import APIRouter, Depends, HTTPException,Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import desc, select
from fastapi import Query

from app.models.rag_search_audit_log import RagSearchAuditLog
from pydantic import BaseModel, ConfigDict, Field
from app.api.dependencies import require_roles
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.rag import (
    RagChunkMatchResponse,
    RagSearchRequest,
    RagSearchResponse,
    RagSearchAuditLogResponse,
)
from app.services.rag_audit_service import create_rag_search_audit_log
from app.services.rag_search_service import search_approved_gold_chunks


router = APIRouter(prefix="/rag", tags=["RAG"])


@router.post(
    "/search",
    response_model=RagSearchResponse,
)
async def rag_search(
    search_request: RagSearchRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles(["Admin", "Editor", "Viewer"])),
) -> RagSearchResponse:
    try:
        search_result = search_approved_gold_chunks(
            query=search_request.query,
            limit=search_request.limit,
            min_score=search_request.min_score,
        )

        await create_rag_search_audit_log(
            db=db,
            current_user=current_user,
            query=search_request.query,
            result_limit=search_request.limit,
            min_score=search_request.min_score,
            search_result=search_result,
        )

        await db.commit()

    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return RagSearchResponse(
        query=search_result["query"],
        min_score=search_result["min_score"],
        matches_count=search_result["matches_count"],
        matches=[
            RagChunkMatchResponse(**match)
            for match in search_result["matches"]
        ],
    )

@router.get(
    "/audit-logs",
    response_model=list[RagSearchAuditLogResponse],
)
async def list_rag_search_audit_logs(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles(["Admin"])),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of RAG audit logs to return.",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of RAG audit logs to skip.",
    ),
) -> list[RagSearchAuditLogResponse]:
    result = await db.execute(
        select(RagSearchAuditLog)
        .order_by(desc(RagSearchAuditLog.created_at))
        .limit(limit)
        .offset(offset)
    )

    logs = result.scalars().all()

    return [
        RagSearchAuditLogResponse.model_validate(log)
        for log in logs
    ]

@router.get(
    "/audit-logs",
    response_model=list[RagSearchAuditLogResponse],
)
async def list_rag_search_audit_logs(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles(["Admin"])),
    actor_user_id: uuid.UUID | None = Query(
        default=None,
        description="Filter RAG audit logs by user ID.",
    ),
    query_contains: str | None = Query(
        default=None,
        min_length=1,
        max_length=200,
        description="Filter RAG audit logs where the query contains this text.",
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
        default=20,
        ge=1,
        le=100,
        description="Maximum number of RAG audit logs to return.",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of RAG audit logs to skip.",
    ),
) -> list[RagSearchAuditLogResponse]:
    query_stmt = select(RagSearchAuditLog)

    if actor_user_id is not None:
        query_stmt = query_stmt.where(
            RagSearchAuditLog.actor_user_id == actor_user_id
        )

    if query_contains:
        query_stmt = query_stmt.where(
            RagSearchAuditLog.query.ilike(f"%{query_contains.strip()}%")
        )

    if date_from is not None:
        query_stmt = query_stmt.where(
            RagSearchAuditLog.created_at >= date_from
        )

    if date_to is not None:
        query_stmt = query_stmt.where(
            RagSearchAuditLog.created_at <= date_to
        )

    query_stmt = (
        query_stmt
        .order_by(desc(RagSearchAuditLog.created_at))
        .limit(limit)
        .offset(offset)
    )

    result = await db.execute(query_stmt)
    logs = result.scalars().all()

    return [
        RagSearchAuditLogResponse.model_validate(log)
        for log in logs
    ]