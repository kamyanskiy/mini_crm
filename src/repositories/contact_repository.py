"""Contact repository."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.contact import Contact
from models.deal import Deal
from repositories.base import BaseRepository


class ContactRepository(BaseRepository[Contact]):
    """Repository for Contact operations."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Contact, db)

    async def has_deals(self, contact_id: int) -> bool:
        """Check if contact has any deals."""
        result = await self.db.execute(
            select(func.count(Deal.id)).where(Deal.contact_id == contact_id)
        )
        count: int = result.scalar_one()  # type: ignore[assignment]
        return count > 0

    async def list_by_owner(
        self, organization_id: int, owner_id: int, skip: int = 0, limit: int = 100
    ) -> list[Contact]:
        """List contacts by owner within organization."""
        result = await self.db.execute(
            select(Contact)
            .where(Contact.organization_id == organization_id, Contact.owner_id == owner_id)
            .offset(skip)
            .limit(limit)
        )
        contacts: list[Contact] = list(result.scalars().all())
        return contacts

    async def list_with_filters(
        self,
        organization_id: int,
        owner_id: int | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Contact]:
        """List contacts with filters."""
        query = select(Contact).where(Contact.organization_id == organization_id)

        if owner_id:
            query = query.where(Contact.owner_id == owner_id)

        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                (Contact.name.ilike(search_pattern)) | (Contact.email.ilike(search_pattern))
            )

        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        contacts: list[Contact] = list(result.scalars().all())
        return contacts
