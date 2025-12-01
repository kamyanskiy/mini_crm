"""Contact service with business logic."""

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ConflictError, ResourceNotFound
from models.contact import Contact
from repositories.contact_repository import ContactRepository
from schemas.contact import ContactCreate, ContactUpdate


class ContactService:
    """Service for contact business logic."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ContactRepository(db)

    async def create_contact(
        self, data: ContactCreate, organization_id: int, owner_id: int
    ) -> Contact:
        """Create a new contact."""
        return await self.repo.create(
            name=data.name,
            email=data.email,
            phone=data.phone,
            organization_id=organization_id,
            owner_id=owner_id,
        )

    async def get_contact(self, contact_id: int, organization_id: int) -> Contact:
        """Get contact by ID."""
        contact = await self.repo.get_by_id_in_org(contact_id, organization_id)
        if not contact:
            raise ResourceNotFound("Contact not found")
        return contact

    async def update_contact(self, contact: Contact, data: ContactUpdate) -> Contact:
        """Update contact."""
        update_data = data.model_dump(exclude_unset=True)
        return await self.repo.update(contact, **update_data)

    async def delete_contact(self, contact: Contact) -> None:
        """
        Delete contact.

        Business Rule: Cannot delete contact if it has any deals.
        """
        has_deals = await self.repo.has_deals(contact.id)
        if has_deals:
            raise ConflictError(
                "Cannot delete contact with existing deals. Remove or reassign deals first."
            )
        await self.repo.delete(contact)

    async def list_contacts(
        self,
        organization_id: int,
        owner_id: int | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Contact]:
        """List contacts with optional filters."""
        contacts: list[Contact] = await self.repo.list_with_filters(
            organization_id=organization_id,
            owner_id=owner_id,
            search=search,
            skip=skip,
            limit=limit,
        )
        return contacts
