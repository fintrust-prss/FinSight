"""
Generic Base Repository.

Provides typed CRUD helpers that all concrete repositories inherit.
Services import concrete repository classes; they never see raw SQLAlchemy
sessions or queries directly.
"""

from __future__ import annotations

from typing import Any, Generic, Sequence, Type, TypeVar

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """
    Generic async repository with common CRUD operations.

    Args:
        session: SQLAlchemy async session (injected per request by FastAPI dep).
        model: The ORM model class this repository manages.
    """

    def __init__(self, session: AsyncSession, model: Type[ModelT]) -> None:
        self._session = session
        self._model = model

    async def get_by_id(self, id: str) -> ModelT | None:
        """Fetch a single record by surrogate primary key."""
        result = await self._session.execute(
            select(self._model).where(self._model.id == id)  # type: ignore[attr-defined]
        )
        return result.scalars().first()

    async def get_all(self, limit: int = 100, offset: int = 0) -> Sequence[ModelT]:
        """Fetch a paginated list of all records."""
        result = await self._session.execute(
            select(self._model).limit(limit).offset(offset)
        )
        return result.scalars().all()

    async def create(self, instance: ModelT) -> ModelT:
        """Persist a new ORM instance and flush to get server defaults."""
        self._session.add(instance)
        await self._session.flush()
        await self._session.refresh(instance)
        return instance

    async def update(self, instance: ModelT, updates: dict[str, Any]) -> ModelT:
        """Apply a dict of field updates to an existing instance."""
        for field, value in updates.items():
            setattr(instance, field, value)
        await self._session.flush()
        await self._session.refresh(instance)
        return instance

    async def delete_by_id(self, id: str) -> bool:
        """Delete by surrogate PK. Returns True if a row was deleted."""
        result = await self._session.execute(
            delete(self._model).where(self._model.id == id)  # type: ignore[attr-defined]
        )
        return result.rowcount > 0

    async def count(self) -> int:
        """Return total count of rows in the table."""
        from sqlalchemy import func
        result = await self._session.execute(
            select(func.count()).select_from(self._model)
        )
        return result.scalar_one()
