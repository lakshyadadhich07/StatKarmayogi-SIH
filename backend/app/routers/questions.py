import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import QuestionDifficulty, QuestionStatus, RoleName
from app.models.user import User
from app.schemas.question import (
    QuestionGenerateRequest,
    QuestionListResponse,
    QuestionResponse,
    QuestionReviewRequest,
    QuestionReviewResponse,
)
from app.services.question_service import QuestionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/questions", tags=["Questions"])


@router.post(
    "/generate",
    response_model=List[QuestionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Generate grounded MCQs for a processed document using Mistral AI RAG",
)
def generate_questions(
    request: QuestionGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.TRAINER, RoleName.ADMIN)),
) -> List[QuestionResponse]:
    """Generates multiple-choice questions grounded in the chunks of a processed document.
    
    Pipeline:
    1. Validates document is PROCESSED.
    2. Loads competency constraints from PostgreSQL if competency_id is supplied.
    3. Retrieves top relevant chunks from ChromaDB vector store.
    4. Formats grounding context with explicit chunk IDs.
    5. Calls Mistral LLM with structured output and strict grounding prompt.
    6. Validates 4 distinct options, valid key, explicit chunk attribution, and intra-batch uniqueness.
    7. Atomically persists questions with PENDING_REVIEW status and increments generation_count in one transaction.

    Restricted to TRAINER and ADMIN roles.
    """
    logger.info(
        f"User {current_user.id} ({current_user.role.name}) initiating MCQ generation "
        f"for document_id={request.document_id}, count={request.num_questions}, "
        f"competency_id={request.competency_id}"
    )
    questions = QuestionService.generate_questions(
        db=db,
        request=request,
        current_user=current_user,
    )
    return [QuestionResponse.model_validate(q) for q in questions]


@router.get(
    "",
    response_model=QuestionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List questions with optional filtering and pagination",
)
def list_questions(
    document_id: Optional[int] = Query(None, description="Filter by document ID"),
    status_filter: Optional[QuestionStatus] = Query(
        None, alias="status", description="Filter by review status (e.g. PENDING_REVIEW)"
    ),
    competency_id: Optional[int] = Query(None, description="Filter by competency ID"),
    difficulty: Optional[QuestionDifficulty] = Query(None, description="Filter by difficulty level"),
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(50, ge=1, le=100, description="Page limit"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.TRAINER, RoleName.SME, RoleName.ADMIN)),
) -> QuestionListResponse:
    """Lists questions with filtering options. Accessible to TRAINER, SME, and ADMIN roles."""
    total, items = QuestionService.list_questions(
        db=db,
        document_id=document_id,
        status=status_filter,
        competency_id=competency_id,
        difficulty=difficulty,
        skip=skip,
        limit=limit,
    )
    return QuestionListResponse(
        total=total,
        items=[QuestionResponse.model_validate(q) for q in items],
    )


@router.get(
    "/{question_id}",
    response_model=QuestionResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve question detail by ID",
)
def get_question(
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.TRAINER, RoleName.SME, RoleName.ADMIN)),
) -> QuestionResponse:
    """Retrieves full details of an individual MCQ, including options, explanation,
    source chunk ID, and page attribution. Accessible to TRAINER, SME, and ADMIN.
    """
    question = QuestionService.get_question_by_id(db=db, question_id=question_id)
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question with ID {question_id} was not found.",
        )
    return QuestionResponse.model_validate(question)


@router.post(
    "/{question_id}/review",
    response_model=QuestionReviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit SME review decision (APPROVE or REJECT) for a pending question",
)
def review_question(
    question_id: int,
    review_request: QuestionReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.SME, RoleName.ADMIN)),
) -> QuestionReviewResponse:
    """Records an SME review decision for an MCQ awaiting review.

    - Restricted to SME and ADMIN roles.
    - Question must currently have status PENDING_REVIEW.
    - Updates question.status to APPROVED or REJECTED.
    - Creates an auditable QuestionReview record with reviewer ID, action, and comment.
    - Commits both changes atomically in a single database transaction.
    """
    logger.info(
        f"User {current_user.id} ({current_user.role.name}) reviewing question {question_id}: "
        f"action={review_request.action.value}"
    )
    review_record, updated_question = QuestionService.review_question(
        db=db,
        question_id=question_id,
        review_request=review_request,
        current_user=current_user,
    )
    return QuestionReviewResponse(
        id=review_record.id,
        question_id=review_record.question_id,
        reviewer_id=review_record.reviewer_id,
        action=review_record.action,
        comment=review_record.comment,
        created_at=review_record.created_at,
        question_status=updated_question.status,
        question=QuestionResponse.model_validate(updated_question),
    )
