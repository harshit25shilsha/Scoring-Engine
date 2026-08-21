import asyncio

from sqlalchemy import select

from app.core.api_keys import create_api_key
from app.database.models import ApiKey
from app.database.postgres import PostgresSessionLocal


async def main():
    async with PostgresSessionLocal() as db:
        existing = await db.execute(
            select(ApiKey).where(ApiKey.scope == "key_admin", ApiKey.status == "active")
        )
        if existing.scalar_one_or_none() is not None:
            print("A key_admin API key already exists; creating another would violate the bootstrap contract.")
            return

        admin_key = await create_api_key(
            db,
            name="key_admin",
            scope="key_admin",
            rate_limit_per_minute=120,
        )

        print("Created bootstrap key_admin. Save the raw key below; it is shown only once.")
        print(f"key_admin: {admin_key}")


if __name__ == "__main__":
    asyncio.run(main())
