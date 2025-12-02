"""Initialize admin user on startup."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import logger, settings
from core.security import hash_password
from models.organization import Organization
from models.organization_member import MemberRole, OrganizationMember
from models.user import User


async def init_admin_user(db: AsyncSession) -> None:
    """
    Create initial admin user if enabled and doesn't exist.

    This function checks if admin creation is enabled and creates an admin user
    with OWNER role in a default organization if the user doesn't already exist.
    """
    if not settings.create_admin_on_startup:
        return

    try:
        # Check if admin user exists
        result = await db.execute(select(User).where(User.email == settings.admin_email))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            logger.info(f"Admin user already exists: {settings.admin_email}")
            return

        # Create admin user
        hashed_password = hash_password(settings.admin_password)
        admin_user = User(
            email=settings.admin_email,
            hashed_password=hashed_password,
            name=settings.admin_name,
            is_active=True,
        )
        db.add(admin_user)
        await db.flush()

        logger.info(f"✓ Admin user created: {admin_user.email} (ID: {admin_user.id})")

        # Check if organization exists
        result = await db.execute(
            select(Organization).where(Organization.name == settings.admin_organization)
        )
        organization = result.scalar_one_or_none()

        if not organization:
            # Create default organization
            organization = Organization(name=settings.admin_organization)
            db.add(organization)
            await db.flush()
            logger.info(f"✓ Organization created: {organization.name} (ID: {organization.id})")
        else:
            logger.info(
                f"✓ Using existing organization: {organization.name} (ID: {organization.id})"
            )

        # Add admin as OWNER
        member = OrganizationMember(
            organization_id=organization.id,
            user_id=admin_user.id,
            role=MemberRole.OWNER,
        )
        db.add(member)

        await db.commit()

        logger.info(f"✓ Admin user '{admin_user.email}' assigned as OWNER of '{organization.name}'")
        logger.info("=" * 60)
        logger.info("ADMIN CREDENTIALS:")
        logger.info(f"  Email: {admin_user.email}")
        logger.info(f"  Password: {settings.admin_password}")
        logger.info("  ⚠️  CHANGE PASSWORD IMMEDIATELY IN PRODUCTION!")
        logger.info("=" * 60)

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create admin user: {e}")
        # Don't raise - allow app to start even if admin creation fails
