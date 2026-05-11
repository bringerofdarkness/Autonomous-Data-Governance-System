import asyncio

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.role import Role
from app.models.user import User


settings = get_settings()


async def create_first_admin() -> None:
    async with AsyncSessionLocal() as session:
        existing_user_result = await session.execute(
            select(User).where(User.email == settings.FIRST_ADMIN_EMAIL)
        )
        existing_user = existing_user_result.scalar_one_or_none()

        if existing_user:
            print("Admin user already exists.")
            return

        admin_role_result = await session.execute(
            select(Role).where(Role.name == "Admin")
        )
        admin_role = admin_role_result.scalar_one_or_none()

        if not admin_role:
            raise RuntimeError("Admin role does not exist. Run role seeder first.")

        admin_user = User(
            email=settings.FIRST_ADMIN_EMAIL,
            full_name="ADGS Admin",
            hashed_password=hash_password(settings.FIRST_ADMIN_PASSWORD),
            is_active=True,
            roles=[admin_role],
        )

        session.add(admin_user)
        await session.commit()

        print("First admin user created successfully.")


async def main() -> None:
    await create_first_admin()


if __name__ == "__main__":
    asyncio.run(main())