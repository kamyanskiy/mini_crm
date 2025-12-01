"""Deal repository."""

from decimal import Decimal

from sqlalchemy import asc, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.deal import Deal, DealStage, DealStatus
from repositories.base import BaseRepository


class DealRepository(BaseRepository[Deal]):
    """Repository for Deal operations."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Deal, db)

    async def get_with_activities(self, deal_id: int) -> Deal | None:
        """Get deal with activities loaded."""
        result = await self.db.execute(
            select(Deal).options(selectinload(Deal.activities)).where(Deal.id == deal_id)
        )
        return result.scalar_one_or_none()

    async def list_by_owner(
        self, organization_id: int, owner_id: int, skip: int = 0, limit: int = 100
    ) -> list[Deal]:
        """List deals by owner within organization."""
        result = await self.db.execute(
            select(Deal)
            .where(Deal.organization_id == organization_id, Deal.owner_id == owner_id)
            .offset(skip)
            .limit(limit)
        )
        deals: list[Deal] = list(result.scalars().all())
        return deals

    async def list_with_filters(
        self,
        organization_id: int,
        owner_id: int | None = None,
        status: list[DealStatus] | None = None,
        stage: DealStage | None = None,
        min_amount: Decimal | None = None,
        max_amount: Decimal | None = None,
        order_by: str = "created_at",
        order: str = "desc",
        skip: int = 0,
        limit: int = 100,
    ) -> list[Deal]:
        """List deals with filters and sorting."""
        query = select(Deal).where(Deal.organization_id == organization_id)

        if owner_id:
            query = query.where(Deal.owner_id == owner_id)

        if status:
            query = query.where(Deal.status.in_(status))

        if stage:
            query = query.where(Deal.stage == stage)

        if min_amount is not None:
            query = query.where(Deal.amount >= min_amount)

        if max_amount is not None:
            query = query.where(Deal.amount <= max_amount)

        # Sorting
        order_column = getattr(Deal, order_by, Deal.created_at)
        if order.lower() == "asc":
            query = query.order_by(asc(order_column))
        else:
            query = query.order_by(desc(order_column))

        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        deals: list[Deal] = list(result.scalars().all())
        return deals
