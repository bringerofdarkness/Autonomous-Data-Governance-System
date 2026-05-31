import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, select

from app.models.rag_search_audit_log import RagSearchAuditLog
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
from app.services.llm_service import LLMGenerationService  # NEW: Import synthesis engine

router = APIRouter(prefix="/rag", tags=["RAG"])

# Initialize our new strict synthesis engine
llm_service = LLMGenerationService()

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
        # 1. Fetch similarity matches using your local vector embedding configuration
        search_result = search_approved_gold_chunks(
            query=search_request.query,
            limit=search_request.limit,
            min_score=search_request.min_score,
        )

        # 2. Extract matches list for processing
        matches_list = search_result.get("matches", [])

        # 3. Process structural context snippets through our deterministic factory layer
        # Re-formatting payload matches internally to map smoothly into text chunks
        formatted_chunks = [
            {
                "text": m.get("text", ""),
                "point_id": m.get("point_id") or str(m.get("id", uuid.uuid4())),
                "metadata": m.get("metadata", {})
            }
            for m in matches_list
        ]

        synthesis_pack = llm_service.synthesize_answer(
            question=search_request.query,
            chunks=formatted_chunks
        )

        # 4. Save search traces securely to your PostgreSQL relational audit logs
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
            detail=f"Secure RAG processing encountered an error: {str(exc)}",
        )

    # 5. Build response object using Pydantic parameters
    # Note: If your RagSearchResponse schema doesn't have synthesized_answer yet, 
    # it will ignore it or you can append it cleanly to your schema profile later.
    return RagSearchResponse(
        query=search_result["query"],
        min_score=search_result["min_score"],
        matches_count=search_result["matches_count"],
        matches=[
            RagChunkMatchResponse(**match)
            for match in matches_list
        ],
        # Assigning the safe context response payload dynamically
        synthesized_answer=synthesis_pack["answer"]
    )


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