from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description=(
        "StatKarmayogi Backend API — AI-Driven Competency Assessment & "
        "Adaptive iGOT Learning Pathway for MoSPI (SIH26101)"
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration allowing frontend clients (Streamlit on 8501, React, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Root"])
def read_root():
    """Root entrypoint returning basic API metadata."""
    return {
        "app": settings.APP_NAME,
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint for monitoring and container orchestration."""
    return {"status": "ok"}


# Register API v1 Routers
from app.routers import (  # noqa: E402
    assessments_router,
    auth_router,
    courses_router,
    documents_router,
    questions_router,
    recommendations_router,
    verification_router,
)

app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(documents_router, prefix=settings.API_V1_PREFIX)
app.include_router(questions_router, prefix=settings.API_V1_PREFIX)
app.include_router(assessments_router, prefix=settings.API_V1_PREFIX)
app.include_router(courses_router, prefix=settings.API_V1_PREFIX)
app.include_router(recommendations_router, prefix=settings.API_V1_PREFIX)
app.include_router(verification_router, prefix=settings.API_V1_PREFIX)
