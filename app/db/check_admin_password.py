import asyncio

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import verify_password
from app.db.session import AsyncSessionLocal
from app.models.user import User


settings = get_settings()


async def check_admin_password() -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.email == settings.FIRST_ADMIN_EMAIL)
        )
        user = result.scalar_one_or_none()

        if user is None:
            print("Admin user not found.")
            return

        print(f"Admin email: {user.email}")
        print(f"Is active: {user.is_active}")
        print(
            "Password valid:",
            verify_password(settings.FIRST_ADMIN_PASSWORD, user.hashed_password),
        )


if __name__ == "__main__":
    asyncio.run(check_admin_password())