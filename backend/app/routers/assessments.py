import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import AssessmentStatus, RoleName
from app.models.user import User
from app.schemas.assessment import (
    AssessmentCreateRequest,
    AssessmentDetailResponse,
    AssessmentListResponse,
    AssessmentResponse,
    AssessmentResultResponse,
    AssessmentSubmitRequest,
    ReassessmentComparisonResponse,
    ReassessmentCreateRequest,
    ReassessmentListResponse,
)
from app.services.assessment_service import AssessmentService
from app.services.reassessment_service import ReassessmentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assessments", tags=["Assessments"])


@router.post(
    "",
    response_model=AssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create and initialize a diagnostic assessment with approved questions",
)
def create_assessment(
    request: AssessmentCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.OFFICER, RoleName.ADMIN)),
) -> AssessmentResponse:
    """Creates a new diagnostic assessment and deterministically assigns approved competency-tagged questions.
    
    Rules:
    - Only APPROVED questions with competency_id IS NOT NULL are selected.
    - Deterministic ordering: questions.id ASC.
    - If called by an OFFICER, the assessment is assigned to themselves.
    - If called by an ADMIN, an officer_id can be specified.
    - TRAINER and SME roles are forbidden from creating assessments (403).
    """
    logger.info(
        f"User {current_user.id} ({current_user.role.name}) initiating assessment creation "
        f"(count={request.question_count}, competency_id={request.competency_id}, document_id={request.document_id})"
    )
    assessment = AssessmentService.create_assessment(
        db=db,
        request=request,
        current_user=current_user,
    )
    return AssessmentResponse.model_validate(assessment)


@router.get(
    "",
    response_model=AssessmentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List assessments with ownership filtering and pagination",
)
def list_assessments(
    status_filter: Optional[AssessmentStatus] = Query(None, alias="status", description="Filter by status (IN_PROGRESS, COMPLETED)"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=100, description="Pagination limit"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.OFFICER, RoleName.TRAINER, RoleName.ADMIN)),
) -> AssessmentListResponse:
    """Lists assessments according to RBAC.
    
    - OFFICER sees only their own assessments.
    - TRAINER and ADMIN can view all assessments.
    - SME role receives 403 Forbidden.
    """
    items, total = AssessmentService.list_assessments(
        db=db,
        current_user=current_user,
        status_filter=status_filter,
        skip=skip,
        limit=limit,
    )
    return AssessmentListResponse(
        total=total,
        items=[AssessmentResponse.model_validate(a) for a in items],
    )


@router.get(
    "/{assessment_id}",
    response_model=AssessmentDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get assessment details and assigned questions",
)
def get_assessment(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.OFFICER, RoleName.TRAINER, RoleName.ADMIN)),
) -> AssessmentDetailResponse:
    """Retrieves assessment metadata and assigned questions.
    
    Security Guarantee:
    - While IN_PROGRESS, correct answers, explanations, and citations are strictly masked.
    - Officers cannot view assessments belonging to other officers (403).
    - SME role receives 403 Forbidden.
    """
    return AssessmentService.get_assessment(
        db=db,
        assessment_id=assessment_id,
        current_user=current_user,
    )


@router.post(
    "/{assessment_id}/submit",
    response_model=AssessmentResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Atomically submit all answers, evaluate correctness, and calculate competency results & skill gaps",
)
def submit_assessment(
    assessment_id: int,
    request: AssessmentSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.OFFICER, RoleName.ADMIN)),
) -> AssessmentResultResponse:
    """Submits answers for all assigned questions in an assessment.
    
    Workflow & Validation:
    - Officer ownership strictly enforced (officers can only submit their own assessments).
    - Assessment must be IN_PROGRESS (completed assessments return 400).
    - Every assigned question must be answered (partial/empty submissions return 400).
    - Deterministic evaluation of correctness against Question.correct_option.
    - Competency-wise score computation and proficiency determination.
    - Automatic skill-gap identification persisted in skill_gaps.
    - Single atomic database transaction.
    - SME and TRAINER receive 403 Forbidden.
    """
    logger.info(f"User {current_user.id} ({current_user.role.name}) submitting answers for assessment {assessment_id}")
    return AssessmentService.submit_assessment(
        db=db,
        assessment_id=assessment_id,
        request=request,
        current_user=current_user,
    )


@router.get(
    "/{assessment_id}/result",
    response_model=AssessmentResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve completed assessment evaluation, competency scores, and skill gaps",
)
def get_assessment_result(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.OFFICER, RoleName.TRAINER, RoleName.ADMIN)),
) -> AssessmentResultResponse:
    """Retrieves the evaluated outcome of a completed assessment.
    
    Rules:
    - Only available after assessment is COMPLETED (returns 400 if IN_PROGRESS).
    - Unmasks detailed question reviews with educational explanations and source citations.
    - Enforces ownership: Officer can only view their own result (403 for other officers).
    - TRAINER and ADMIN can inspect results.
    - SME role receives 403 Forbidden.
    """
    return AssessmentService.get_assessment_result(
        db=db,
        assessment_id=assessment_id,
        current_user=current_user,
    )


# ============================================================================
# Phase 9: Reassessment & Closed Learning Loop Endpoints
# ============================================================================

@router.post(
    "/{baseline_id}/reassess",
    response_model=AssessmentDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate a targeted reassessment linked to a completed baseline assessment",
)
def create_reassessment(
    baseline_id: int,
    request: Optional[ReassessmentCreateRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.OFFICER, RoleName.ADMIN)),
) -> AssessmentDetailResponse:
    """Initiates a targeted reassessment linked to an existing completed baseline assessment.
    
    Security & Business Rules:
    - Reassessment targets competencies where baseline skill gaps were identified.
    - Zero schema changes: baseline linkage encoded via canonical title format.
    - Baseline must be COMPLETED (400 if still IN_PROGRESS).
    - Cannot create a reassessment of another reassessment (400).
    - Officer can only create reassessments for their own baseline (403 for other officers).
    - TRAINER and SME roles forbidden from creating reassessments (403).
    - Returns exam-safe masked questions (correct options and explanations hidden).
    """
    logger.info(
        f"User {current_user.id} ({current_user.role.name}) initiating reassessment for baseline {baseline_id}"
    )
    return ReassessmentService.create_reassessment(
        db=db,
        baseline_id=baseline_id,
        request=request,
        current_user=current_user,
    )


@router.get(
    "/{reassessment_id}/comparison",
    response_model=ReassessmentComparisonResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate before-vs-after comparison evaluating the closed learning loop",
)
def get_reassessment_comparison(
    reassessment_id: int,
    baseline_id: Optional[int] = Query(None, description="Optional explicit baseline assessment ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.OFFICER, RoleName.TRAINER, RoleName.ADMIN)),
) -> ReassessmentComparisonResponse:
    """Computes deterministic before/after comparison between baseline and reassessment.
    
    Macro Precedence Evaluation:
    - LOOP_CLOSED: Every baseline gap reached >= 80.0% (ADVANCED, zero baseline gaps unresolved).
    - PARTIALLY_CLOSED: At least one baseline gap is RESOLVED or REDUCED, and at least one baseline deficiency remains unresolved.
    - LOOP_OPEN: Zero baseline gaps improved/reduced, or no baseline gaps qualify for partial closure.
    - Individual competency outcomes and declined competencies reported separately.
    - Preceding completed courses documented as non-causal developmental correlation.
    
    Security:
    - Officer can only inspect their own comparisons (403 for other officers).
    - TRAINER and ADMIN can inspect comparisons across all officers.
    - SME role receives 403 Forbidden.
    """
    return ReassessmentService.get_reassessment_comparison(
        db=db,
        reassessment_id=reassessment_id,
        baseline_id=baseline_id,
        current_user=current_user,
    )


@router.get(
    "/{baseline_id}/reassessments",
    response_model=ReassessmentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all sequential reassessment attempts linked to a baseline assessment",
)
def list_reassessments_for_baseline(
    baseline_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.OFFICER, RoleName.TRAINER, RoleName.ADMIN)),
) -> ReassessmentListResponse:
    """Lists all sequential reassessment attempts linked to a baseline assessment.
    
    Rules:
    - Ordered chronologically: started_at ASC, id ASC (Attempt 1, Attempt 2, etc.).
    - Officer can only view their own baseline's attempts (403 for other officers).
    - TRAINER and ADMIN can view attempts for any officer.
    - SME role receives 403 Forbidden.
    """
    return ReassessmentService.list_reassessments_for_baseline(
        db=db,
        baseline_id=baseline_id,
        current_user=current_user,
    )

