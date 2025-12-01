"""Base repository with generic CRUD operations."""

from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository with common CRUD operations."""

    def __init__(self, model: type[ModelType], db: AsyncSession) -> None:
        self.model = model
        self.db = db

    async def get_by_id(self, id: int) -> ModelType | None:
        """Get entity by ID."""
        result = await self.db.execute(select(self.model).where(self.model.id == id))
        entity: ModelType | None = result.scalar_one_or_none()
        return entity

    async def get_by_id_in_org(self, id: int, organization_id: int) -> ModelType | None:
        """Get entity by ID within specific organization."""
        result = await self.db.execute(
            select(self.model).where(
                self.model.id == id,
                self.model.organization_id == organization_id,  # type: ignore
            )
        )
        entity: ModelType | None = result.scalar_one_or_none()
        return entity

    async def list_in_org(
        self,
        organization_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ModelType]:
        """List entities within specific organization."""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.organization_id == organization_id)  # type: ignore[attr-defined]
            .offset(skip)
            .limit(limit)
        )
        items: list[ModelType] = list(result.scalars().all())
        return items

    async def create(self, **kwargs: Any) -> ModelType:
        """Create new entity."""
        entity: ModelType = self.model(**kwargs)
        self.db.add(entity)
        await self.db.flush()
        await self.db.refresh(entity)
        return entity

    async def update(self, entity: ModelType, **kwargs: Any) -> ModelType:
        """Update entity."""
        for key, value in kwargs.items():
            if value is not None:
                setattr(entity, key, value)
        await self.db.flush()
        await self.db.refresh(entity)
        return entity

    async def delete(self, entity: ModelType) -> None:
        """Delete entity."""
        await self.db.delete(entity)
        await self.db.flush()
