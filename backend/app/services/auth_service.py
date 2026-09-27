from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models.enums import RoleName
from app.models.role import Role
from app.models.user import User
from app.schemas.auth import TokenResponse, UserRegisterRequest
from app.schemas.user import UserResponse


class AuthService:
    """Authentication and registration business logic service."""

    @staticmethod
    def register_user(db: Session, reg_data: UserRegisterRequest) -> User:
        """Register a new user with role selected during registration."""
        # Ensure ADMIN accounts cannot be self-registered
        normalized_role = reg_data.role.strip().upper()
        if normalized_role == RoleName.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Public registration as ADMIN is not permitted.",
            )

        # Check for existing email (case-insensitive)
        normalized_email = reg_data.email.strip().lower()
        existing_user = (
            db.query(User)
            .filter(func.lower(User.email) == normalized_email)
            .first()
        )
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email address already exists.",
            )

        # Resolve role against the authoritative roles table
        role = db.query(Role).filter(Role.name == normalized_role).first()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role '{normalized_role}' does not exist in the system.",
            )

        # Hash password and create active user record
        password_hashed = hash_password(reg_data.password)
        new_user = User(
            name=reg_data.name.strip(),
            email=normalized_email,
            password_hash=password_hashed,
            role_id=role.id,
            department=reg_data.department.strip() if reg_data.department else None,
            designation=reg_data.designation.strip() if reg_data.designation else None,
            is_active=True,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user

    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> User:
        """Authenticate user credentials without exposing whether email exists."""
        normalized_email = email.strip().lower()
        user = (
            db.query(User)
            .filter(func.lower(User.email) == normalized_email)
            .first()
        )

        # Constant-time-like rejection for non-existent users or password mismatch
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Inactive account verification
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive. Please contact an administrator.",
            )

        return user

    @staticmethod
    def generate_token_response(user: User) -> TokenResponse:
        """Generate JWT access token and return safe user profile."""
        role_name = user.role.name if user.role else "OFFICER"
        token_data = {
            "sub": str(user.id),
            "role": role_name,
        }
        access_token = create_access_token(data=token_data)
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse(
                id=user.id,
                name=user.name,
                email=user.email,
                role=role_name,
            ),
        )
