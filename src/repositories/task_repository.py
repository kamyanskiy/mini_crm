"""Task repository."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.deal import Deal
from models.task import Task
from repositories.base import BaseRepository


class TaskRepository(BaseRepository[Task]):
    """Repository for Task operations."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Task, db)

    async def list_by_deal(self, deal_id: int) -> list[Task]:
        """List all tasks for a deal."""
        result = await self.db.execute(select(Task).where(Task.deal_id == deal_id))
        tasks: list[Task] = list(result.scalars().all())
        return tasks

    async def get_deal_for_task(self, task_id: int) -> Deal | None:
        """Get the deal associated with a task."""
        result = await self.db.execute(select(Deal).join(Task).where(Task.id == task_id))
        return result.scalar_one_or_none()

    async def list_with_filters(
        self,
        organization_id: int,
        deal_id: int | None = None,
        only_open: bool | None = None,
        due_before: datetime | None = None,
        due_after: datetime | None = None,
        owner_id: int | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Task]:
        """List tasks with filters, scoped to organization."""
        # Join with Deal to filter by organization
        query = select(Task).join(Deal).where(Deal.organization_id == organization_id)

        if owner_id:
            query = query.where(Deal.owner_id == owner_id)

        if deal_id:
            query = query.where(Task.deal_id == deal_id)

        if only_open is not None:
            query = query.where(Task.is_done == (not only_open))

        if due_before:
            query = query.where(Task.due_date <= due_before)

        if due_after:
            query = query.where(Task.due_date >= due_after)

        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        tasks: list[Task] = list(result.scalars().all())
        return tasks
