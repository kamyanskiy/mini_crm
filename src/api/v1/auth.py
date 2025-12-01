"""Authentication routes."""

from fastapi import APIRouter, status

from api.dependencies.auth import CurrentUser
from core.database import DBSession
from core.security import verify_token
from schemas.user import TokenResponse, UserCreate, UserLogin, UserResponse
from services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description=(
        "Create a new user account with email and password. Email must be unique across the system."
    ),
)
async def register(data: UserCreate, db: DBSession) -> UserResponse:
    service = AuthService(db)
    user = await service.register_user(data)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and get access token",
    description=(
        "Authenticate user with email and password. "
        "Returns both access token (15min TTL) and refresh token (7 days TTL)."
    ),
)
async def login(data: UserLogin, db: DBSession) -> TokenResponse:
    service = AuthService(db)
    user = await service.authenticate_user(data.email, data.password)
    tokens = service.create_tokens(user.id)
    return TokenResponse(**tokens)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description=(
        "Generate a new access token using a valid refresh token. "
        "Returns new access token and refresh token."
    ),
)
async def refresh(refresh_token: str, db: DBSession) -> TokenResponse:
    user_id = verify_token(refresh_token, token_type="refresh")
    service = AuthService(db)
    tokens = await service.refresh_tokens(user_id)
    return TokenResponse(**tokens)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user info",
    description="Retrieve profile information for the currently authenticated user.",
)
async def get_current_user_info(current_user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(current_user)
