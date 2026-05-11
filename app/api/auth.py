from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.auth import TokenResponse
from app.services.auth_service import authenticate_user, create_user_access_token


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    user = await authenticate_user(
        db=db,
        email=form_data.username,
        password=form_data.password,
    )

    access_token = create_user_access_token(user)

    return TokenResponse(access_token=access_token)