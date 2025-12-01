"""Unit tests for deal business logic."""

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import BusinessRuleViolation, PermissionDenied
from models.deal import Deal, DealStage, DealStatus
from models.organization import Organization
from models.organization_member import MemberRole
from models.types import AuthContext
from models.user import User
from schemas.deal import DealCreate, DealUpdate
from services.deal_service import DealService


class TestDealCreationRules:
    """Test deal creation business rules."""

    @pytest.mark.asyncio
    async def test_create_deal_with_contact_from_same_org(
        self, db_session: AsyncSession, organization: Organization, owner_user: User, contact
    ):
        """Should allow creating deal with contact from same organization."""
        service = DealService(db_session)
        deal_data = DealCreate(
            title="Test Deal",
            contact_id=contact.id,
            amount=Decimal("1000.00"),
            currency="USD",
            status=DealStatus.NEW,
            stage=DealStage.QUALIFICATION,
        )

        deal = await service.create_deal(deal_data, organization.id, owner_user.id)

        assert deal.title == "Test Deal"
        assert deal.contact_id == contact.id
        assert deal.organization_id == organization.id

    @pytest.mark.asyncio
    async def test_create_deal_with_contact_from_different_org_fails(
        self,
        db_session: AsyncSession,
        organization: Organization,
        other_organization: Organization,
        owner_user: User,
        contact,
    ):
        """Business Rule: Cannot link contact from different organization."""
        service = DealService(db_session)
        deal_data = DealCreate(
            title="Test Deal",
            contact_id=contact.id,  # Contact belongs to 'organization'
            amount=Decimal("1000.00"),
        )

        with pytest.raises(BusinessRuleViolation) as exc:
            await service.create_deal(
                deal_data,
                other_organization.id,
                owner_user.id,  # Different org
            )

        assert "does not belong to this organization" in str(exc.value)


class TestDealStatusTransitionRules:
    """Test deal status transition business rules."""

    @pytest.mark.asyncio
    async def test_cannot_close_deal_as_won_with_zero_amount(
        self, db_session: AsyncSession, deal: Deal, owner_user: User
    ):
        """Business Rule: Cannot close deal as won if amount <= 0."""
        service = DealService(db_session)
        auth_context = AuthContext(
            user_id=owner_user.id, organization_id=deal.organization_id, role=MemberRole.OWNER
        )

        # Set amount to 0
        deal.amount = Decimal("0")
        await db_session.commit()

        update_data = DealUpdate(status=DealStatus.WON)

        with pytest.raises(BusinessRuleViolation) as exc:
            await service.update_deal(deal, update_data, auth_context)

        assert "amount <= 0" in str(exc.value)

    @pytest.mark.asyncio
    async def test_cannot_close_deal_as_won_with_negative_amount(
        self, db_session: AsyncSession, deal: Deal, owner_user: User
    ):
        """Business Rule: Pydantic validation prevents negative amounts."""
        from pydantic import ValidationError

        # Schema validation should prevent negative amounts
        with pytest.raises(ValidationError):
            DealUpdate(status=DealStatus.WON, amount=Decimal("-100"))

    @pytest.mark.asyncio
    async def test_can_close_deal_as_won_with_positive_amount(
        self, db_session: AsyncSession, deal: Deal, owner_user: User
    ):
        """Should allow closing deal as won with positive amount."""
        service = DealService(db_session)
        auth_context = AuthContext(
            user_id=owner_user.id, organization_id=deal.organization_id, role=MemberRole.OWNER
        )

        deal.amount = Decimal("1000.00")
        await db_session.commit()

        update_data = DealUpdate(status=DealStatus.WON)
        updated_deal = await service.update_deal(deal, update_data, auth_context)

        assert updated_deal.status == DealStatus.WON

    @pytest.mark.asyncio
    async def test_status_change_to_won_creates_activity(
        self, db_session: AsyncSession, deal: Deal, owner_user: User
    ):
        """Business Rule: Status change to won should create activity."""
        service = DealService(db_session)
        auth_context = AuthContext(
            user_id=owner_user.id, organization_id=deal.organization_id, role=MemberRole.OWNER
        )

        deal.amount = Decimal("1000.00")
        await db_session.commit()

        update_data = DealUpdate(status=DealStatus.WON)
        await service.update_deal(deal, update_data, auth_context)

        # Verify activity was created
        updated_deal = await service.get_deal_with_activities(deal.id, deal.organization_id)
        assert len(updated_deal.activities) > 0
        activity = updated_deal.activities[0]
        assert activity.type.value == "status_changed"
        assert activity.payload["new_status"] == "won"


class TestDealStageTransitionRules:
    """Test deal stage transition business rules."""

    @pytest.mark.asyncio
    async def test_member_cannot_rollback_stage(
        self, db_session: AsyncSession, deal_in_negotiation: Deal, member_user: User
    ):
        """Business Rule: Members cannot rollback deal stages."""
        service = DealService(db_session)
        auth_context = AuthContext(
            user_id=member_user.id,
            organization_id=deal_in_negotiation.organization_id,
            role=MemberRole.MEMBER,
        )

        # Try to move from NEGOTIATION to PROPOSAL (backward)
        update_data = DealUpdate(stage=DealStage.PROPOSAL)

        with pytest.raises(PermissionDenied) as exc:
            await service.update_deal(deal_in_negotiation, update_data, auth_context)

        assert "rollback" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_manager_cannot_rollback_stage(
        self, db_session: AsyncSession, deal_in_negotiation: Deal, manager_user: User
    ):
        """Business Rule: Managers cannot rollback deal stages."""
        service = DealService(db_session)
        auth_context = AuthContext(
            user_id=manager_user.id,
            organization_id=deal_in_negotiation.organization_id,
            role=MemberRole.MANAGER,
        )

        update_data = DealUpdate(stage=DealStage.QUALIFICATION)

        with pytest.raises(PermissionDenied) as exc:
            await service.update_deal(deal_in_negotiation, update_data, auth_context)

        assert "rollback" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_admin_can_rollback_stage(
        self, db_session: AsyncSession, deal_in_negotiation: Deal, admin_user: User
    ):
        """Business Rule: Admins can rollback deal stages."""
        service = DealService(db_session)
        auth_context = AuthContext(
            user_id=admin_user.id,
            organization_id=deal_in_negotiation.organization_id,
            role=MemberRole.ADMIN,
        )

        update_data = DealUpdate(stage=DealStage.PROPOSAL)
        updated_deal = await service.update_deal(deal_in_negotiation, update_data, auth_context)

        assert updated_deal.stage == DealStage.PROPOSAL

    @pytest.mark.asyncio
    async def test_owner_can_rollback_stage(
        self, db_session: AsyncSession, deal_in_negotiation: Deal, owner_user: User
    ):
        """Business Rule: Owners can rollback deal stages."""
        service = DealService(db_session)
        auth_context = AuthContext(
            user_id=owner_user.id,
            organization_id=deal_in_negotiation.organization_id,
            role=MemberRole.OWNER,
        )

        update_data = DealUpdate(stage=DealStage.QUALIFICATION)
        updated_deal = await service.update_deal(deal_in_negotiation, update_data, auth_context)

        assert updated_deal.stage == DealStage.QUALIFICATION

    @pytest.mark.asyncio
    async def test_forward_stage_transition_allowed_for_all_roles(
        self, db_session: AsyncSession, deal: Deal, member_user: User
    ):
        """Business Rule: Forward stage transitions are allowed for all roles."""
        service = DealService(db_session)
        auth_context = AuthContext(
            user_id=member_user.id, organization_id=deal.organization_id, role=MemberRole.MEMBER
        )

        # Move from QUALIFICATION to PROPOSAL (forward)
        update_data = DealUpdate(stage=DealStage.PROPOSAL)
        updated_deal = await service.update_deal(deal, update_data, auth_context)

        assert updated_deal.stage == DealStage.PROPOSAL

    @pytest.mark.asyncio
    async def test_stage_change_creates_activity(
        self, db_session: AsyncSession, deal: Deal, owner_user: User
    ):
        """Business Rule: Stage change should create activity."""
        service = DealService(db_session)
        auth_context = AuthContext(
            user_id=owner_user.id, organization_id=deal.organization_id, role=MemberRole.OWNER
        )

        update_data = DealUpdate(stage=DealStage.PROPOSAL)
        await service.update_deal(deal, update_data, auth_context)

        # Verify activity was created
        updated_deal = await service.get_deal_with_activities(deal.id, deal.organization_id)
        activities = [a for a in updated_deal.activities if a.type.value == "stage_changed"]
        assert len(activities) > 0
        activity = activities[0]
        assert activity.payload["old_stage"] == "qualification"
        assert activity.payload["new_stage"] == "proposal"
