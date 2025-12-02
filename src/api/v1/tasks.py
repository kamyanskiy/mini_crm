"""Task routes."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from api.dependencies.organization import OrgContextDep
from api.dependencies.pagination import PaginationParams
from core.database import DBSession
from models.types import AuthContext
from schemas.task import TaskCreate, TaskResponse, TaskUpdate
from services.task_service import TaskService

PaginationDep = Annotated[PaginationParams, Depends()]

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get(
    "",
    response_model=list[TaskResponse],
    summary="List tasks",
)
async def list_tasks(
    org_context: OrgContextDep,
    db: DBSession,
    pagination: PaginationDep,
    deal_id: int | None = Query(None, gt=0, description="Filter by deal ID"),
    only_open: bool | None = Query(None, description="Show only incomplete tasks"),
    due_before: datetime | None = Query(None, description="Filter tasks due before this datetime"),
    due_after: datetime | None = Query(None, description="Filter tasks due after this datetime"),
) -> list[TaskResponse]:
    """
    List tasks in the organization with optional filtering and pagination.

    Query parameters:
    - **page** - Page number (starts from 1)
    - **page_size** - Number of items per page (max 100)
    - **deal_id** - Filter tasks by specific deal ID
    - **only_open** - If true, show only incomplete tasks (is_done=false)
    - **due_before** - Filter tasks due before this datetime
    - **due_after** - Filter tasks due after this datetime

    Members can only see tasks for their own deals. Managers and above can see all tasks.
    """
    service = TaskService(db)

    # Convert HTTP context to domain AuthContext
    auth_context = AuthContext(
        user_id=org_context.user_id,
        organization_id=org_context.organization_id,
        role=org_context.role,
    )

    tasks = await service.list_tasks(
        auth_context=auth_context,
        deal_id=deal_id,
        only_open=only_open,
        due_before=due_before,
        due_after=due_after,
        skip=pagination.skip,
        limit=pagination.limit,
    )
    return [TaskResponse.model_validate(t) for t in tasks]


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task",
)
async def create_task_general(
    data: TaskCreate,
    org_context: OrgContextDep,
    db: DBSession,
    deal_id: int = Query(..., gt=0, description="Deal ID for the task"),
) -> TaskResponse:
    """
    Create a new task (general endpoint).

    Business rules:
    - **Members can only create tasks for their own deals**
    - **due_date must be today or in the future** - cannot create overdue tasks
    """
    service = TaskService(db)

    # Convert HTTP context to domain AuthContext
    auth_context = AuthContext(
        user_id=org_context.user_id,
        organization_id=org_context.organization_id,
        role=org_context.role,
    )

    task = await service.create_task(data, deal_id, auth_context)
    return TaskResponse.model_validate(task)


@router.get(
    "/deals/{deal_id}/tasks",
    response_model=list[TaskResponse],
    summary="List tasks for a deal",
    description=(
        "Retrieve all tasks associated with a specific deal. "
        "Members can only view tasks for their own deals."
    ),
)
async def list_tasks_for_deal(
    *,
    deal_id: int = Path(..., gt=0, description="Deal ID"),
    org_context: OrgContextDep,
    db: DBSession,
) -> list[TaskResponse]:
    service = TaskService(db)

    # Convert HTTP context to domain AuthContext
    auth_context = AuthContext(
        user_id=org_context.user_id,
        organization_id=org_context.organization_id,
        role=org_context.role,
    )

    tasks = await service.list_tasks_for_deal(deal_id, auth_context)
    return [TaskResponse.model_validate(t) for t in tasks]


@router.post(
    "/deals/{deal_id}/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create task for a deal",
)
async def create_task(
    *,
    deal_id: int = Path(..., gt=0, description="Deal ID"),
    data: TaskCreate,
    org_context: OrgContextDep,
    db: DBSession,
) -> TaskResponse:
    """
    Create a new task for a specific deal.

    Business rules:
    - **Members can only create tasks for their own deals**
    - **due_date must be today or in the future** - cannot create overdue tasks
    """
    service = TaskService(db)

    # Convert HTTP context to domain AuthContext
    auth_context = AuthContext(
        user_id=org_context.user_id,
        organization_id=org_context.organization_id,
        role=org_context.role,
    )

    task = await service.create_task(data, deal_id, auth_context)
    return TaskResponse.model_validate(task)


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Update task",
    description=(
        "Partially update task information. Members can only update tasks for their own deals."
    ),
)
async def update_task(
    *,
    task_id: int = Path(..., gt=0, description="Task ID"),
    data: TaskUpdate,
    org_context: OrgContextDep,
    db: DBSession,
) -> TaskResponse:
    service = TaskService(db)

    # Convert HTTP context to domain AuthContext
    auth_context = AuthContext(
        user_id=org_context.user_id,
        organization_id=org_context.organization_id,
        role=org_context.role,
    )

    task = await service.get_task(task_id, auth_context)
    task = await service.update_task(task, data, auth_context)
    return TaskResponse.model_validate(task)


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete task",
    description="Delete a task. Members can only delete tasks for their own deals.",
)
async def delete_task(
    *,
    task_id: int = Path(..., gt=0, description="Task ID"),
    org_context: OrgContextDep,
    db: DBSession,
) -> None:
    service = TaskService(db)

    # Convert HTTP context to domain AuthContext
    auth_context = AuthContext(
        user_id=org_context.user_id,
        organization_id=org_context.organization_id,
        role=org_context.role,
    )

    task = await service.get_task(task_id, auth_context)
    await service.delete_task(task, auth_context)
