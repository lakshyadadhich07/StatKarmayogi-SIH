import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.enums import RecommendationStatus, RoleName
from app.models.user import User
from app.schemas.recommendation import (
    RecommendationListResponse,
    RecommendationResponse,
    RecommendationStatusUpdateRequest,
)
from app.services.recommendation_service import RecommendationService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Recommendations"])


@router.post(
    "/assessments/{assessment_id}/recommendations",
    response_model=List[RecommendationResponse],
    status_code=status.HTTP_200_OK,
    summary="Generate or regenerate course recommendations for a completed assessment",
)
def generate_recommendations(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.OFFICER, RoleName.ADMIN)),
) -> List[RecommendationResponse]:
    """Generates explainable recommendations based on diagnostic skill gaps.
    
    - Officer can generate for their own assessments.
    - Admin can generate for any assessment.
    - Trainers and SMEs are forbidden (403).
    - Preserves historical records (STARTED, COMPLETED, DISMISSED).
    """
    logger.info(f"User {current_user.id} requested recommendations generation for assessment {assessment_id}")
    return RecommendationService.generate_recommendations(
        db=db,
        assessment_id=assessment_id,
        current_user=current_user,
    )


@router.get(
    "/assessments/{assessment_id}/recommendations",
    response_model=List[RecommendationResponse],
    status_code=status.HTTP_200_OK,
    summary="List recommendations for a specific assessment",
)
def list_assessment_recommendations(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.OFFICER, RoleName.TRAINER, RoleName.ADMIN)),
) -> List[RecommendationResponse]:
    """Retrieves all recommendations linked to a specific assessment.
    
    - Officer sees only recommendations for their own assessments.
    - Trainer and Admin can inspect across all assessments.
    - SME receives 403 Forbidden.
    """
    return RecommendationService.list_assessment_recommendations(
        db=db,
        assessment_id=assessment_id,
        current_user=current_user,
    )


@router.get(
    "/recommendations",
    response_model=RecommendationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List recommendations across assessments with optional filters",
)
def list_recommendations(
    assessment_id: Optional[int] = Query(None, description="Filter by assessment ID"),
    status_filter: Optional[RecommendationStatus] = Query(None, alias="status", description="Filter by status (RECOMMENDED, STARTED, COMPLETED, DISMISSED)"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=100, description="Pagination limit"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.OFFICER, RoleName.TRAINER, RoleName.ADMIN)),
) -> RecommendationListResponse:
    """List recommendations with filtering and pagination.
    
    - Officer sees only their own recommendations.
    - Trainer and Admin can view all recommendations.
    - SME receives 403 Forbidden.
    """
    return RecommendationService.list_recommendations(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
        status_filter=status_filter,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/recommendations/{recommendation_id}",
    response_model=RecommendationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single recommendation detail",
)
def get_recommendation(
    recommendation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.OFFICER, RoleName.TRAINER, RoleName.ADMIN)),
) -> RecommendationResponse:
    """Retrieve details for a single recommendation.
    
    - Officer can only inspect their own recommendations.
    - Trainer and Admin can inspect any recommendation.
    - SME receives 403 Forbidden.
    """
    return RecommendationService.get_recommendation(
        db=db,
        recommendation_id=recommendation_id,
        current_user=current_user,
    )


@router.patch(
    "/recommendations/{recommendation_id}/status",
    response_model=RecommendationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update recommendation status along the valid state machine",
)
def update_recommendation_status(
    recommendation_id: int,
    request: RecommendationStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.OFFICER, RoleName.ADMIN)),
) -> RecommendationResponse:
    """Progresses recommendation status (e.g. RECOMMENDED -> STARTED -> COMPLETED or RECOMMENDED -> DISMISSED).
    
    - Enforces ownership: Only assigned Officer or Admin can update status.
    - Terminal states (COMPLETED, DISMISSED) cannot transition further.
    - Trainers and SMEs are forbidden (403).
    """
    return RecommendationService.update_recommendation_status(
        db=db,
        recommendation_id=recommendation_id,
        request=request,
        current_user=current_user,
    )
