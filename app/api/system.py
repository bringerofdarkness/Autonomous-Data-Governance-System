from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import require_roles
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