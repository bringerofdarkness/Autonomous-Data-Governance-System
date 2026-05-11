import asyncio

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.role import Role


DEFAULT_ROLES = [
    {
        "name": "Admin",
        "description": "Full system access. Can approve documents and manage governance workflows.",
    },
    {
        "name": "Editor",
        "description": "Can upload documents and view processing status.",
    },
    {
        "name": "Viewer",
        "description": "Can only view reports and audit logs.",
    },
]


async def seed_roles() -> None:
    async with AsyncSessionLocal() as session:
        for role_data in DEFAULT_ROLES:
            result = await session.execute(
                select(Role).where(Role.name == role_data["name"])
            )
            existing_role = result.scalar_one_or_none()

            if existing_role:
                continue

            role = Role(
                name=role_data["name"],
                description=role_data["description"],
            )
            session.add(role)

        await session.commit()


async def main() -> None:
    await seed_roles()
    print("Default roles seeded successfully.")


if __name__ == "__main__":
    asyncio.run(main())