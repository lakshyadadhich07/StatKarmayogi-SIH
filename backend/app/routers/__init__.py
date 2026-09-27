"""API route handlers package."""
from app.routers.assessments import router as assessments_router
from app.routers.auth import router as auth_router
from app.routers.courses import router as courses_router
from app.routers.documents import router as documents_router
from app.routers.questions import router as questions_router
from app.routers.recommendations import router as recommendations_router
from app.routers.verification import router as verification_router

__all__ = [
    "assessments_router",
    "auth_router",
    "courses_router",
    "documents_router",
    "questions_router",
    "recommendations_router",
    "verification_router",
]
