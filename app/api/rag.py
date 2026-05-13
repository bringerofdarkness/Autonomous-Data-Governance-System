from fastapi import APIRouter, Depends, HTTPException, status
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