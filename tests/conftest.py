"""Pytest fixtures for testing."""

import asyncio
import sys
from collections.abc import AsyncGenerator
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# Add src directory to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

import os  # noqa: E402

from core import redis  # noqa: E402
from core.cache import RedisCache  # noqa: E402

# Test database - use separate test DB
from core.config import settings  # noqa: E402
from core.security import hash_password  # noqa: E402
from main import app  # noqa: E402
from models.base import Base  # noqa: E402
from models.contact import Contact  # noqa: E402
from models.deal import Deal, DealStage, DealStatus  # noqa: E402
from models.organization import Organization  # noqa: E402
from models.organization_member import MemberRole, OrganizationMember  # noqa: E402
from models.user import User  # noqa: E402

# For tests, use localhost instead of docker container name
TEST_DB_HOST = os.getenv("TEST_POSTGRES_HOST", "localhost")
TEST_DB_NAME = f"{settings.postgres_db}_test"
TEST_DATABASE_URL = (
    f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}"
    f"@{TEST_DB_HOST}:{settings.postgres_port}/{TEST_DB_NAME}"
)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_db_setup():
    """Create and drop test database."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine as create_engine_sync

    # Connect to default postgres db to create test db
    admin_url = (
        f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}"
        f"@{TEST_DB_HOST}:{settings.postgres_port}/postgres"
    )
    admin_engine = create_engine_sync(admin_url, isolation_level="AUTOCOMMIT")

    # Drop test DB if exists and create fresh one
    async with admin_engine.connect() as conn:
        await conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}"))
        await conn.execute(text(f"CREATE DATABASE {TEST_DB_NAME}"))

    await admin_engine.dispose()

    yield

    # Cleanup - drop test database
    admin_engine = create_engine_sync(admin_url, isolation_level="AUTOCOMMIT")
    async with admin_engine.connect() as conn:
        await conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}"))
    await admin_engine.dispose()


@pytest.fixture(scope="function")
async def engine(test_db_setup):
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session


@pytest.fixture
def mock_cache():
    """Create mock cache for tests."""
    mock = AsyncMock(spec=RedisCache)
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=True)
    mock.delete_pattern = AsyncMock(return_value=True)
    mock.get_json = AsyncMock(return_value=None)
    mock.set_json = AsyncMock(return_value=True)
    return mock


@pytest.fixture
async def client(db_session: AsyncSession, mock_cache) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with database and cache override."""
    from core.database import get_db

    async def override_get_db():
        yield db_session

    # Mock redis cache
    redis.cache = mock_cache

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
async def owner_user(db_session: AsyncSession) -> User:
    """Create a test owner user."""
    user = User(
        email="owner@test.com",
        name="Test Owner",
        hashed_password=hash_password("password123"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create a test admin user."""
    user = User(
        email="admin@test.com",
        name="Test Admin",
        hashed_password=hash_password("password123"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def manager_user(db_session: AsyncSession) -> User:
    """Create a test manager user."""
    user = User(
        email="manager@test.com",
        name="Test Manager",
        hashed_password=hash_password("password123"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def member_user(db_session: AsyncSession) -> User:
    """Create a test member user."""
    user = User(
        email="member@test.com",
        name="Test Member",
        hashed_password=hash_password("password123"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def other_member_user(db_session: AsyncSession) -> User:
    """Create another test member user."""
    user = User(
        email="other_member@test.com",
        name="Other Member",
        hashed_password=hash_password("password123"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def organization(db_session: AsyncSession, owner_user: User) -> Organization:
    """Create a test organization."""
    org = Organization(name="Test Organization")
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)

    # Add owner as member
    member = OrganizationMember(
        organization_id=org.id, user_id=owner_user.id, role=MemberRole.OWNER
    )
    db_session.add(member)
    await db_session.commit()

    return org


@pytest.fixture
async def other_organization(db_session: AsyncSession, owner_user: User) -> Organization:
    """Create another test organization for isolation testing."""
    org = Organization(name="Other Organization")
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)

    # Add owner as member
    member = OrganizationMember(
        organization_id=org.id, user_id=owner_user.id, role=MemberRole.OWNER
    )
    db_session.add(member)
    await db_session.commit()

    return org


@pytest.fixture
async def organization_with_members(
    db_session: AsyncSession,
    organization: Organization,
    admin_user: User,
    manager_user: User,
    member_user: User,
    other_member_user: User,
) -> Organization:
    """Add all test users to organization with their roles."""
    members = [
        OrganizationMember(
            organization_id=organization.id, user_id=admin_user.id, role=MemberRole.ADMIN
        ),
        OrganizationMember(
            organization_id=organization.id, user_id=manager_user.id, role=MemberRole.MANAGER
        ),
        OrganizationMember(
            organization_id=organization.id, user_id=member_user.id, role=MemberRole.MEMBER
        ),
        OrganizationMember(
            organization_id=organization.id,
            user_id=other_member_user.id,
            role=MemberRole.MEMBER,
        ),
    ]
    db_session.add_all(members)
    await db_session.commit()
    return organization


@pytest.fixture
async def contact(
    db_session: AsyncSession, organization: Organization, owner_user: User
) -> Contact:
    """Create a test contact."""
    contact = Contact(
        name="Test Contact",
        email="contact@test.com",
        phone="+1234567890",
        organization_id=organization.id,
        owner_id=owner_user.id,
    )
    db_session.add(contact)
    await db_session.commit()
    await db_session.refresh(contact)
    return contact


@pytest.fixture
async def contact_for_member(
    db_session: AsyncSession, organization: Organization, member_user: User
) -> Contact:
    """Create a contact owned by member."""
    contact = Contact(
        name="Member Contact",
        email="member_contact@test.com",
        organization_id=organization.id,
        owner_id=member_user.id,
    )
    db_session.add(contact)
    await db_session.commit()
    await db_session.refresh(contact)
    return contact


@pytest.fixture
async def deal(
    db_session: AsyncSession, organization: Organization, owner_user: User, contact: Contact
) -> Deal:
    """Create a test deal."""
    deal = Deal(
        title="Test Deal",
        amount=Decimal("1000.00"),
        currency="USD",
        status=DealStatus.NEW,
        stage=DealStage.QUALIFICATION,
        organization_id=organization.id,
        owner_id=owner_user.id,
        contact_id=contact.id,
    )
    db_session.add(deal)
    await db_session.commit()
    await db_session.refresh(deal)
    return deal


@pytest.fixture
async def deal_for_member(
    db_session: AsyncSession,
    organization: Organization,
    member_user: User,
    contact_for_member: Contact,
) -> Deal:
    """Create a deal owned by member."""
    deal = Deal(
        title="Member Deal",
        amount=Decimal("500.00"),
        currency="USD",
        status=DealStatus.NEW,
        stage=DealStage.QUALIFICATION,
        organization_id=organization.id,
        owner_id=member_user.id,
        contact_id=contact_for_member.id,
    )
    db_session.add(deal)
    await db_session.commit()
    await db_session.refresh(deal)
    return deal


@pytest.fixture
async def deal_in_negotiation(
    db_session: AsyncSession, organization: Organization, owner_user: User
) -> Deal:
    """Create a deal in negotiation stage."""
    deal = Deal(
        title="Negotiation Deal",
        amount=Decimal("5000.00"),
        currency="USD",
        status=DealStatus.IN_PROGRESS,
        stage=DealStage.NEGOTIATION,
        organization_id=organization.id,
        owner_id=owner_user.id,
    )
    db_session.add(deal)
    await db_session.commit()
    await db_session.refresh(deal)
    return deal


async def get_auth_headers(client: AsyncClient, email: str, password: str = "password123") -> dict:
    """Get authentication headers for a user."""
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def owner_headers(client: AsyncClient, owner_user: User) -> dict:
    """Get auth headers for owner user."""
    return await get_auth_headers(client, owner_user.email)


@pytest.fixture
async def admin_headers(client: AsyncClient, admin_user: User) -> dict:
    """Get auth headers for admin user."""
    return await get_auth_headers(client, admin_user.email)


@pytest.fixture
async def manager_headers(client: AsyncClient, manager_user: User) -> dict:
    """Get auth headers for manager user."""
    return await get_auth_headers(client, manager_user.email)


@pytest.fixture
async def member_headers(client: AsyncClient, member_user: User) -> dict:
    """Get auth headers for member user."""
    return await get_auth_headers(client, member_user.email)


@pytest.fixture
async def other_member_headers(client: AsyncClient, other_member_user: User) -> dict:
    """Get auth headers for other member user."""
    return await get_auth_headers(client, other_member_user.email)
