from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user, require_roles
from app.models.enums import RoleName
from app.models.user import User

router = APIRouter(prefix="/test", tags=["Authorization Verification (Test Only)"])


@router.get("/authenticated")
def verify_authenticated(current_user: User = Depends(get_current_user)):
    """Verifies that the request has a valid JWT for an active user."""
    return {
        "status": "authenticated",
        "user_id": current_user.id,
        "email": current_user.email,
        "role": current_user.role.name if current_user.role else None,
    }


@router.get("/trainer")
def verify_trainer_endpoint(
    current_user: User = Depends(require_roles(RoleName.TRAINER)),
):
    """Protected endpoint accessible only by users with TRAINER role."""
    return {
        "message": "Welcome Trainer",
        "user_id": current_user.id,
        "role": current_user.role.name,
    }


@router.get("/sme")
def verify_sme_endpoint(
    current_user: User = Depends(require_roles(RoleName.SME)),
):
    """Protected endpoint accessible only by users with SME role."""
    return {
        "message": "Welcome SME",
        "user_id": current_user.id,
        "role": current_user.role.name,
    }


@router.get("/officer")
def verify_officer_endpoint(
    current_user: User = Depends(require_roles(RoleName.OFFICER)),
):
    """Protected endpoint accessible only by users with OFFICER role."""
    return {
        "message": "Welcome Officer",
        "user_id": current_user.id,
        "role": current_user.role.name,
    }


@router.get("/admin")
def verify_admin_endpoint(
    current_user: User = Depends(require_roles(RoleName.ADMIN)),
):
    """Protected endpoint accessible only by users with ADMIN role."""
    return {
        "message": "Welcome Admin",
        "user_id": current_user.id,
        "role": current_user.role.name,
    }
