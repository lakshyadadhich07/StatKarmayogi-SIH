import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.competency import Competency
from app.models.course import Course
from app.models.course_competency import CourseCompetency
from app.models.enums import RoleName
from app.models.user import User
from app.schemas.course import (
    CourseCompetencyResponse,
    CourseDetailResponse,
    CourseListResponse,
    CourseResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/courses", tags=["Courses"])


@router.get(
    "",
    response_model=CourseListResponse,
    status_code=status.HTTP_200_OK,
    summary="List courses from the iGOT-aligned prototype catalogue",
)
def list_courses(
    query: Optional[str] = Query(None, description="Search term in title or description"),
    competency_id: Optional[int] = Query(None, description="Filter by linked competency ID"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty level"),
    language: Optional[str] = Query(None, description="Filter by language"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=100, description="Pagination limit"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.OFFICER, RoleName.TRAINER, RoleName.ADMIN, RoleName.SME)),
) -> CourseListResponse:
    """Browse courses available in the local iGOT-aligned catalogue.
    
    Accessible to all authenticated roles (OFFICER, TRAINER, ADMIN, SME).
    """
    q = db.query(Course).filter(Course.is_active == True)

    if query:
        q_term = f"%{query.strip()}%"
        q = q.filter((Course.title.ilike(q_term)) | (Course.description.ilike(q_term)))

    if difficulty:
        q = q.filter(Course.difficulty.ilike(difficulty.strip()))

    if language:
        q = q.filter(Course.language.ilike(language.strip()))

    if competency_id:
        q = q.join(CourseCompetency, Course.id == CourseCompetency.course_id).filter(
            CourseCompetency.competency_id == competency_id
        )

    total = q.count()
    courses = q.order_by(Course.id.asc()).offset(skip).limit(limit).all()

    return CourseListResponse(
        total=total,
        items=[CourseResponse.model_validate(c) for c in courses],
    )


@router.get(
    "/{course_id}",
    response_model=CourseDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get course detail with linked competencies",
)
def get_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.OFFICER, RoleName.TRAINER, RoleName.ADMIN, RoleName.SME)),
) -> CourseDetailResponse:
    """Retrieve full details of a course including its mapped competencies and relevance scores."""
    course = db.query(Course).filter(Course.id == course_id, Course.is_active == True).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with ID {course_id} not found.",
        )

    # Fetch associated competencies
    mappings = (
        db.query(CourseCompetency, Competency)
        .join(Competency, CourseCompetency.competency_id == Competency.id)
        .filter(CourseCompetency.course_id == course_id)
        .all()
    )

    comp_items: List[CourseCompetencyResponse] = [
        CourseCompetencyResponse(
            competency_id=c.id,
            competency_code=c.code,
            competency_name=c.name,
            relevance_score=float(cc.relevance_score),
        )
        for cc, c in mappings
    ]

    course_data = CourseResponse.model_validate(course).model_dump()
    return CourseDetailResponse(**course_data, competencies=comp_items)
