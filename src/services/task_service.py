"""Task service with business logic."""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import PermissionDenied, ResourceNotFound
from models.task import Task
from models.types import AuthContext
from repositories.deal_repository import DealRepository
from repositories.task_repository import TaskRepository
from schemas.task import TaskCreate, TaskUpdate


class TaskService:
    """Service for task business logic."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = TaskRepository(db)
        self.deal_repo = DealRepository(db)

    async def create_task(self, data: TaskCreate, deal_id: int, auth_context: AuthContext) -> Task:
        """
        Create a new task.

        Business Rules:
        - Member can only create tasks for their own deals
        - due_date validation is handled by schema
        """
        # Get the deal to check ownership
        deal = await self.deal_repo.get_by_id_in_org(deal_id, auth_context.organization_id)
        if not deal:
            raise ResourceNotFound("Deal not found")

        # Members can only create tasks for their own deals
        if auth_context.is_member() and deal.owner_id != auth_context.user_id:
            raise PermissionDenied("Members can only create tasks for their own deals")

        return await self.repo.create(
            deal_id=deal_id,
            title=data.title,
            description=data.description,
            due_date=data.due_date,
            is_done=False,
        )

    async def get_task(self, task_id: int, auth_context: AuthContext) -> Task:
        """Get task by ID and validate organization."""
        task = await self.repo.get_by_id(task_id)
        if not task:
            raise ResourceNotFound("Task not found")

        # Verify task belongs to a deal in the current organization
        deal = await self.deal_repo.get_by_id(task.deal_id)
        if not deal or deal.organization_id != auth_context.organization_id:
            raise ResourceNotFound("Task not found")

        return task

    async def update_task(self, task: Task, data: TaskUpdate, auth_context: AuthContext) -> Task:
        """
        Update task.

        Business Rules:
        - Members can only update their own tasks
        """
        # Get associated deal
        deal = await self.deal_repo.get_by_id(task.deal_id)
        if not deal:
            raise ResourceNotFound("Deal not found")

        # Members can only update their own tasks
        if auth_context.is_member() and deal.owner_id != auth_context.user_id:
            raise PermissionDenied("Members can only update their own tasks")

        update_data = data.model_dump(exclude_unset=True)
        return await self.repo.update(task, **update_data)

    async def delete_task(self, task: Task, auth_context: AuthContext) -> None:
        """
        Delete task.

        Business Rules:
        - Members can only delete their own tasks
        """
        # Get associated deal
        deal = await self.deal_repo.get_by_id(task.deal_id)
        if not deal:
            raise ResourceNotFound("Deal not found")

        # Members can only delete their own tasks
        if auth_context.is_member() and deal.owner_id != auth_context.user_id:
            raise PermissionDenied("Members can only delete their own tasks")

        await self.repo.delete(task)

    async def list_tasks_for_deal(self, deal_id: int, auth_context: AuthContext) -> list[Task]:
        """List all tasks for a deal."""
        # Verify deal exists and belongs to organization
        deal = await self.deal_repo.get_by_id_in_org(deal_id, auth_context.organization_id)
        if not deal:
            raise ResourceNotFound("Deal not found")

        tasks: list[Task] = await self.repo.list_by_deal(deal_id)
        return tasks

    async def list_tasks(
        self,
        auth_context: AuthContext,
        deal_id: int | None = None,
        only_open: bool | None = None,
        due_before: datetime | None = None,
        due_after: datetime | None = None,
    ) -> list[Task]:
        """List tasks with filters."""
        # Members only see their own tasks
        owner_id = auth_context.user_id if auth_context.is_member() else None

        tasks: list[Task] = await self.repo.list_with_filters(
            organization_id=auth_context.organization_id,
            deal_id=deal_id,
            only_open=only_open,
            due_before=due_before,
            due_after=due_after,
            owner_id=owner_id,
        )
        return tasks
