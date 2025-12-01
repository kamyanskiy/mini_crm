"""Unit tests for contact business logic."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ConflictError
from models.contact import Contact
from models.organization import Organization
from models.user import User
from schemas.contact import ContactCreate
from services.contact_service import ContactService


class TestContactDeletionRules:
    """Test contact deletion business rules."""

    @pytest.mark.asyncio
    async def test_cannot_delete_contact_with_deals(
        self, db_session: AsyncSession, contact: Contact, deal
    ):
        """Business Rule: Cannot delete contact if it has deals."""
        service = ContactService(db_session)

        # Contact has a deal associated (from fixture)
        with pytest.raises(ConflictError) as exc:
            await service.delete_contact(contact)

        assert "existing deals" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_can_delete_contact_without_deals(
        self, db_session: AsyncSession, organization: Organization, owner_user: User
    ):
        """Should allow deleting contact without deals."""
        service = ContactService(db_session)

        # Create contact without deals
        contact_data = ContactCreate(name="No Deals Contact", email="nodeals@test.com")
        contact = await service.create_contact(contact_data, organization.id, owner_user.id)

        # Should delete successfully
        await service.delete_contact(contact)

        # Verify deletion
        with pytest.raises(Exception):
            await service.get_contact(contact.id, organization.id)
