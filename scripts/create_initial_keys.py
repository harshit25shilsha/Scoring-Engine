import asyncio

from app.core.api_keys import create_api_key
from app.database.postgres import PostgresSessionLocal


async def main():
    async with PostgresSessionLocal() as db:
        admin_key = await create_api_key(
            db,
            name="admin-cli",
            scope="admin",
            rate_limit_per_minute=120,
        )
        frontend_key = await create_api_key(
            db,
            name="frontend-dev",
            scope="read",
            rate_limit_per_minute=100,
        )

        print(f"ADMIN KEY (save now, shown once): {admin_key}")
        print(f"FRONTEND KEY (save now, shown once): {frontend_key}")


if __name__ == "__main__":
    asyncio.run(main())
