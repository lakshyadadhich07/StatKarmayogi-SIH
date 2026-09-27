from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import TokenResponse, UserLoginRequest, UserRegisterRequest
from app.schemas.user import UserMeResponse, UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Registers a new user with a specified role (TRAINER, SME, OFFICER). ADMIN cannot be self-registered.",
)
def register(
    reg_data: UserRegisterRequest,
    db: Session = Depends(get_db),
):
    """Register user with role chosen during registration."""
    new_user = AuthService.register_user(db, reg_data)
    return UserResponse(
        id=new_user.id,
        name=new_user.name,
        email=new_user.email,
        role=new_user.role.name if new_user.role else reg_data.role,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate user and obtain JWT",
    description="Authenticate with email and password (no role field). Returns JWT access token with stored user role.",
)
def login(
    login_data: UserLoginRequest,
    db: Session = Depends(get_db),
):
    """Login with email and password without role selection."""
    user = AuthService.authenticate_user(db, login_data.email, login_data.password)
    return AuthService.generate_token_response(user)


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="OAuth2 compatible token login for Swagger UI",
    description="OAuth2 password flow accepting username (email) and password as application/x-www-form-urlencoded.",
)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    """OAuth2 password form login returning standard JWT token response."""
    user = AuthService.authenticate_user(db, form_data.username, form_data.password)
    return AuthService.generate_token_response(user)


@router.get(
    "/me",
    response_model=UserMeResponse,
    summary="Get current authenticated user profile",
    description="Returns detailed profile information for the authenticated user from the authoritative database record.",
)
def get_me(
    current_user: User = Depends(get_current_user),
):
    """Retrieve profile for the currently authenticated user."""
    return UserMeResponse(
        id=current_user.id,
        name=current_user.name,
        email=current_user.email,
        role=current_user.role.name if current_user.role else "",
        department=current_user.department,
        designation=current_user.designation,
        is_active=current_user.is_active,
    )
