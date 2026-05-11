import asyncio

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.role import Role
from app.models.user import User


TEST_USERS = [
    {
        "email": "editor@adgs.com",
        "password": "Test@12345",
        "full_name": "ADGS Editor",
        "role": "Editor",
    },
    {
        "email": "viewer@adgs.com",
        "password": "Test@12345",
        "full_name": "ADGS Viewer",
        "role": "Viewer",
    },
]


async def seed_test_users() -> None:
    async with AsyncSessionLocal() as session:
        for user_data in TEST_USERS:
            existing_user_result = await session.execute(
                select(User).where(User.email == user_data["email"])
            )
            existing_user = existing_user_result.scalar_one_or_none()

            if existing_user:
                print(f"User already exists: {user_data['email']}")
                continue

            role_result = await session.execute(
                select(Role).where(Role.name == user_data["role"])
            )
            role = role_result.scalar_one_or_none()

            if role is None:
                raise RuntimeError(f"Role does not exist: {user_data['role']}")

            user = User(
                email=user_data["email"],
                full_name=user_data["full_name"],
                hashed_password=hash_password(user_data["password"]),
                is_active=True,
                roles=[role],
            )

            session.add(user)
            print(f"Created user: {user_data['email']} with role {user_data['role']}")

        await session.commit()


async def main() -> None:
    await seed_test_users()
    print("Test users seeding completed.")


if __name__ == "__main__":
    asyncio.run(main())