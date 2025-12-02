"""Activity repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.activity import Activity
from repositories.base import BaseRepository


class ActivityRepository(BaseRepository[Activity]):
    """Repository for Activity operations."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Activity, db)

    async def list_by_deal(self, deal_id: int, skip: int = 0, limit: int = 100) -> list[Activity]:
        """List all activities for a deal, ordered by creation time."""
        result = await self.db.execute(
            select(Activity)
            .where(Activity.deal_id == deal_id)
            .order_by(Activity.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        activities: list[Activity] = list(result.scalars().all())
        return activities
