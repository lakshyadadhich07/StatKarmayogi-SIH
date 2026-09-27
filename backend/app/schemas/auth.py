from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator
from app.schemas.user import UserResponse


class UserRegisterRequest(BaseModel):
    """Registration request with role selection."""
    name: str
    email: str
    password: str
    role: str
    department: Optional[str] = None
    designation: Optional[str] = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        v_clean = v.strip().lower()
        if not v_clean or "@" not in v_clean:
            raise ValueError("Invalid email address format.")
        return v_clean

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v_clean = v.strip()
        if not v_clean:
            raise ValueError("Name cannot be blank.")
        return v_clean

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters long.")
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        v_clean = v.strip().upper()
        if v_clean not in ["TRAINER", "SME", "OFFICER"]:
            raise ValueError("Role must be one of: TRAINER, SME, OFFICER. ADMIN cannot be self-registered.")
        return v_clean


class UserLoginRequest(BaseModel):
    """Login request without role selection field."""
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class TokenResponse(BaseModel):
    """JWT bearer token and safe user profile."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

    model_config = ConfigDict(from_attributes=True)
