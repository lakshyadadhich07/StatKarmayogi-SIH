from typing import Optional
from pydantic import BaseModel, ConfigDict


class UserResponse(BaseModel):
    """Safe user profile response without sensitive credentials."""
    id: int
    name: str
    email: str
    role: str

    model_config = ConfigDict(from_attributes=True)


class UserMeResponse(BaseModel):
    """Detailed user profile for authenticated /me endpoint."""
    id: int
    name: str
    email: str
    role: str
    department: Optional[str] = None
    designation: Optional[str] = None
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)
