from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_roles
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.rag import (
    RagChunkMatchResponse,
    RagSearchRequest,
    RagSearchResponse,
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