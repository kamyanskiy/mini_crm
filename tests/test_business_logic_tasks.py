"""Unit tests for task business logic."""

from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import PermissionDenied
from models.deal import Deal
from models.organization_member import MemberRole
from models.task import Task
from models.types import AuthContext
from models.user import User
from schemas.task import TaskCreate, TaskUpdate
from services.task_service import TaskService


class TestTaskCreationRules:
    """Test task creation business rules."""

    @pytest.mark.asyncio
    async def test_member_cannot_create_task_for_other_users_deal(
        self, db_session: AsyncSession, deal: Deal, member_user: User
    ):
        """Business Rule: Member cannot create task for another user's deal."""
        service = TaskService(db_session)
        auth_context = AuthContext(
            user_id=member_user.id, organization_id=deal.organization_id, role=MemberRole.MEMBER
        )

        task_data = TaskCreate(title="Test Task", due_date=datetime.now() + timedelta(days=1))

        with pytest.raises(PermissionDenied) as exc:
            await service.create_task(task_data, deal.id, auth_context)

        assert "own deals" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_member_can_create_task_for_own_deal(
        self, db_session: AsyncSession, deal_for_member: Deal, member_user: User
    ):
        """Members can create tasks for their own deals."""
        service = TaskService(db_session)
        auth_context = AuthContext(
            user_id=member_user.id,
            organization_id=deal_for_member.organization_id,
            role=MemberRole.MEMBER,
        )

        task_data = TaskCreate(title="My Task", due_date=datetime.now() + timedelta(days=1))

        task = await service.create_task(task_data, deal_for_member.id, auth_context)

        assert task.title == "My Task"
        assert task.deal_id == deal_for_member.id

    @pytest.mark.asyncio
    async def test_manager_can_create_task_for_any_deal(
        self, db_session: AsyncSession, deal: Deal, manager_user: User
    ):
        """Managers can create tasks for any deal in organization."""
        service = TaskService(db_session)
        auth_context = AuthContext(
            user_id=manager_user.id, organization_id=deal.organization_id, role=MemberRole.MANAGER
        )

        task_data = TaskCreate(title="Manager Task", due_date=datetime.now() + timedelta(days=1))

        task = await service.create_task(task_data, deal.id, auth_context)

        assert task.title == "Manager Task"

    @pytest.mark.asyncio
    async def test_admin_can_create_task_for_any_deal(
        self, db_session: AsyncSession, deal: Deal, admin_user: User
    ):
        """Admins can create tasks for any deal in organization."""
        service = TaskService(db_session)
        auth_context = AuthContext(
            user_id=admin_user.id, organization_id=deal.organization_id, role=MemberRole.ADMIN
        )

        task_data = TaskCreate(title="Admin Task", due_date=datetime.now() + timedelta(days=1))

        task = await service.create_task(task_data, deal.id, auth_context)

        assert task.title == "Admin Task"


class TestTaskDueDateRules:
    """Test task due_date validation rules."""

    def test_cannot_create_task_with_past_due_date(self):
        """Business Rule: Cannot set due_date in the past."""
        past_date = datetime.now() - timedelta(days=1)

        with pytest.raises(ValidationError) as exc:
            TaskCreate(title="Past Task", due_date=past_date)

        assert "due_date cannot be in the past" in str(exc.value)

    def test_can_create_task_with_today_due_date(self):
        """Can set due_date to today."""
        today = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
        task_data = TaskCreate(title="Today Task", due_date=today)

        assert task_data.due_date == today

    def test_can_create_task_with_future_due_date(self):
        """Can set due_date in the future."""
        future_date = datetime.now() + timedelta(days=7)
        task_data = TaskCreate(title="Future Task", due_date=future_date)

        assert task_data.due_date == future_date

    def test_cannot_update_task_with_past_due_date(self):
        """Business Rule: Cannot update due_date to past."""
        past_date = datetime.now() - timedelta(days=1)

        with pytest.raises(ValidationError) as exc:
            TaskUpdate(due_date=past_date)

        assert "due_date cannot be in the past" in str(exc.value)


class TestTaskUpdateRules:
    """Test task update business rules."""

    @pytest.mark.asyncio
    async def test_member_cannot_update_other_users_task(
        self,
        db_session: AsyncSession,
        organization_with_members,
        member_user: User,
        other_member_user: User,
        contact_for_member,
    ):
        """Business Rule: Member cannot update another member's task."""
        # Create deal owned by other_member_user
        deal = Deal(
            title="Other's Deal",
            organization_id=organization_with_members.id,
            owner_id=other_member_user.id,
            contact_id=contact_for_member.id,
        )
        db_session.add(deal)
        await db_session.commit()

        task = Task(
            deal_id=deal.id, title="Other's Task", due_date=datetime.now() + timedelta(days=1)
        )
        db_session.add(task)
        await db_session.commit()

        service = TaskService(db_session)
        auth_context = AuthContext(
            user_id=member_user.id,
            organization_id=organization_with_members.id,
            role=MemberRole.MEMBER,
        )

        update_data = TaskUpdate(title="Updated Task")

        with pytest.raises(PermissionDenied) as exc:
            await service.update_task(task, update_data, auth_context)

        assert "own tasks" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_manager_can_update_any_task(
        self,
        db_session: AsyncSession,
        organization_with_members,
        manager_user: User,
        owner_user: User,
        contact,
    ):
        """Managers can update any task in organization."""
        # Create deal owned by another user
        deal = Deal(
            title="Deal",
            organization_id=organization_with_members.id,
            owner_id=owner_user.id,  # Use real user ID
            contact_id=contact.id,
        )
        db_session.add(deal)
        await db_session.commit()

        task = Task(deal_id=deal.id, title="Task", due_date=datetime.now() + timedelta(days=1))
        db_session.add(task)
        await db_session.commit()

        service = TaskService(db_session)
        auth_context = AuthContext(
            user_id=manager_user.id,
            organization_id=organization_with_members.id,
            role=MemberRole.MANAGER,
        )

        update_data = TaskUpdate(title="Manager Updated")
        updated_task = await service.update_task(task, update_data, auth_context)

        assert updated_task.title == "Manager Updated"


class TestTaskDeletionRules:
    """Test task deletion business rules."""

    @pytest.mark.asyncio
    async def test_member_cannot_delete_other_users_task(
        self,
        db_session: AsyncSession,
        organization_with_members,
        member_user: User,
        other_member_user: User,
        contact_for_member,
    ):
        """Business Rule: Member cannot delete another member's task."""
        deal = Deal(
            title="Other's Deal",
            organization_id=organization_with_members.id,
            owner_id=other_member_user.id,
            contact_id=contact_for_member.id,
        )
        db_session.add(deal)
        await db_session.commit()

        task = Task(
            deal_id=deal.id, title="Other's Task", due_date=datetime.now() + timedelta(days=1)
        )
        db_session.add(task)
        await db_session.commit()

        service = TaskService(db_session)
        auth_context = AuthContext(
            user_id=member_user.id,
            organization_id=organization_with_members.id,
            role=MemberRole.MEMBER,
        )

        with pytest.raises(PermissionDenied) as exc:
            await service.delete_task(task, auth_context)

        assert "own tasks" in str(exc.value).lower()
