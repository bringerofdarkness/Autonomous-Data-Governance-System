from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import require_roles
from app.models.user import User
from app.schemas.rag import (
    RagChunkMatchResponse,
    RagSearchRequest,
    RagSearchResponse,
)
from app.services.rag_search_service import search_approved_gold_chunks


router = APIRouter(prefix="/rag", tags=["RAG"])


@router.post(
    "/search",
    response_model=RagSearchResponse,
)
async def rag_search(
    search_request: RagSearchRequest,
    current_user: User = Depends(require_roles(["Admin", "Editor", "Viewer"])),
) -> RagSearchResponse:
    try:
        search_result = search_approved_gold_chunks(
            query=search_request.query,
            limit=search_request.limit,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return RagSearchResponse(
        query=search_result["query"],
        matches_count=search_result["matches_count"],
        matches=[
            RagChunkMatchResponse(**match)
            for match in search_result["matches"]
        ],
    )