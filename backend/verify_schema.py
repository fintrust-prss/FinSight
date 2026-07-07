import asyncio
import asyncpg
from app.config import get_settings

settings = get_settings()

async def main():
    conn = await asyncpg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        user=settings.postgres_user,
        password=settings.postgres_password,
        database=settings.postgres_db,
    )
    try:
        tables = await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname = current_schema()")
        print([r['tablename'] for r in tables])
    finally:
        await conn.close()

asyncio.run(main())
