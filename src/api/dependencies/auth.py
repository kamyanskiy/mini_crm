"""Authentication dependencies."""

from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy import select

from core.database import DBSession
from core.exceptions import AuthenticationError, ResourceNotFound
from core.security import verify_token
from models.user import User


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: DBSession = DBSession,
) -> User:
    """
    Get the current authenticated user from JWT token.

    Args:
        authorization: Authorization header (Bearer token)
        db: Database session

    Returns:
        Current user

    Raises:
        AuthenticationError: If authentication fails
    """
    if not authorization:
        raise AuthenticationError("Missing authorization header")

    # Extract token from "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthenticationError("Invalid authorization header format")

    token = parts[1]

    # Verify token and get user_id
    user_id = verify_token(token, token_type="access")

    # Fetch user from database
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise ResourceNotFound("User not found")

    if not user.is_active:
        raise AuthenticationError("User account is inactive")

    return user


# Type alias for dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
