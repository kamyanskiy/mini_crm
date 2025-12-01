"""Authentication service with business logic."""

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import AuthenticationError, BusinessRuleViolation
from core.security import create_access_token, create_refresh_token, hash_password, verify_password
from models.user import User
from repositories.user_repository import UserRepository
from schemas.user import UserCreate


class AuthService:
    """Service for authentication and user management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.user_repo = UserRepository(db)

    async def register_user(self, data: UserCreate) -> User:
        """
        Register a new user.

        Business Rule: Email must be unique.
        """
        # Check if user already exists
        existing_user = await self.user_repo.get_by_email(data.email)
        if existing_user:
            raise BusinessRuleViolation("Email already registered")

        # Hash password and create user
        hashed_password = hash_password(data.password)
        user = await self.user_repo.create_user(
            email=data.email,
            hashed_password=hashed_password,
            name=data.name,
        )

        return user

    async def authenticate_user(self, email: str, password: str) -> User:
        """
        Authenticate user by email and password.

        Args:
            email: User email
            password: Plain text password

        Returns:
            User object if authentication successful

        Raises:
            AuthenticationError: If credentials are invalid or user is inactive
        """
        # Get user by email
        user = await self.user_repo.get_by_email(email)
        if not user:
            raise AuthenticationError("Incorrect email or password")

        # Verify password
        if not verify_password(password, user.hashed_password):
            raise AuthenticationError("Incorrect email or password")

        # Check if user is active
        if not user.is_active:
            raise AuthenticationError("User account is inactive")

        return user

    def create_tokens(self, user_id: int) -> dict[str, str]:
        """
        Create access and refresh tokens for user.

        Args:
            user_id: User ID

        Returns:
            Dictionary with access_token and refresh_token
        """
        return {
            "access_token": create_access_token(user_id),
            "refresh_token": create_refresh_token(user_id),
        }

    async def refresh_tokens(self, user_id: int) -> dict[str, str]:
        """
        Refresh tokens for user.

        Args:
            user_id: User ID

        Returns:
            New access and refresh tokens

        Raises:
            AuthenticationError: If user not found or inactive
        """
        # Verify user exists and is active
        user = await self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise AuthenticationError("Invalid refresh token")

        return self.create_tokens(user_id)
