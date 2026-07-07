import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import get_settings
from app.db.session import Base
import app.db.models

settings = get_settings()
engine = create_async_engine(settings.database_url)

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()

asyncio.run(main())
