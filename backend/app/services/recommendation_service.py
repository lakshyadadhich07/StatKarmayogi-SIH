from decimal import Decimal
import logging
from typing import Dict, List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.assessment import Assessment
from app.models.competency import Competency
from app.models.course import Course
from app.models.course_competency import CourseCompetency
from app.models.enums import AssessmentStatus, GapLevel, RecommendationStatus, RoleName
from app.models.recommendation import Recommendation
from app.models.skill_gap import SkillGap
from app.models.user import User
from app.schemas.recommendation import (
    LearningPathwayResponse,
    RecommendationListResponse,
    RecommendationResponse,
    RecommendationStatusUpdateRequest,
)

logger = logging.getLogger(__name__)

GAP_WEIGHTS: Dict[GapLevel, Tuple[float, int]] = {
    GapLevel.HIGH: (1.00, 1),
    GapLevel.MEDIUM: (0.85, 2),
    GapLevel.LOW: (0.70, 3),
}

ALLOWED_TRANSITIONS = {
    RecommendationStatus.RECOMMENDED: {RecommendationStatus.STARTED, RecommendationStatus.DISMISSED},
    RecommendationStatus.STARTED: {RecommendationStatus.COMPLETED},
    RecommendationStatus.COMPLETED: set(),
    RecommendationStatus.DISMISSED: set(),
}


class RecommendationService:
    """Service encapsulating 100% deterministic matching, explainable reason generation,
    status state transitions, and history-preserving recommendation reconciliation.
    """

    @classmethod
    def generate_recommendations(
        cls,
        db: Session,
        assessment_id: int,
        current_user: User,
    ) -> List[RecommendationResponse]:
        """Generates or regenerates recommendations for a completed assessment using deterministic rules.
        
        Constraints:
        - Assessment must exist and be COMPLETED.
        - Officer can only generate for their own assessments.
        - Admin can generate for any assessment.
        - Trainer and SME are forbidden (403).
        - If assessment has zero skill gaps, returns empty list without error.
        - Preserves all historical records (STARTED, COMPLETED, DISMISSED).
        - Limits active recommendations to MAX_TOTAL_ACTIVE_RECOMMENDATIONS (6).
        """
        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assessment with ID {assessment_id} not found.",
            )

        # RBAC Check
        user_role = current_user.role.name if current_user.role else ""
        if user_role == RoleName.OFFICER.value and assessment.officer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only generate recommendations for your own assessments.",
            )
        if user_role in {RoleName.TRAINER.value, RoleName.SME.value}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"{user_role} role is not authorized to trigger recommendation generation.",
            )

        if assessment.status != AssessmentStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Recommendations can only be generated for COMPLETED assessments.",
            )

        # Fetch skill gaps
        skill_gaps = (
            db.query(SkillGap)
            .filter(SkillGap.assessment_id == assessment_id)
            .all()
        )

        # No skill gaps -> zero recommendations produced cleanly
        if not skill_gaps:
            logger.info(f"Assessment {assessment_id} has no skill gaps. Returning empty recommendations list.")
            return []

        # Load competencies map
        comp_ids = {g.competency_id for g in skill_gaps}
        comps = db.query(Competency).filter(Competency.id.in_(comp_ids)).all()
        comp_map = {c.id: c for c in comps}

        # 1. Deterministic Candidate Matching per Skill Gap
        per_gap_candidates: List[Dict] = []
        for gap in skill_gaps:
            gap_mult, gap_priority = GAP_WEIGHTS.get(gap.gap_level, (0.70, 3))

            # Query course competencies directly from PostgreSQL
            mappings = (
                db.query(CourseCompetency, Course)
                .join(Course, CourseCompetency.course_id == Course.id)
                .filter(
                    CourseCompetency.competency_id == gap.competency_id,
                    Course.is_active == True,
                )
                .all()
            )

            gap_candidates = []
            for cc, course in mappings:
                rel_score_float = float(cc.relevance_score)
                match_score = round(rel_score_float * gap_mult * 100, 2)

                comp = comp_map.get(gap.competency_id)
                comp_name = comp.name if comp else f"Competency {gap.competency_id}"
                score_pct = float(gap.score_percentage)
                gap_val = gap.gap_level.value
                relevance_pct = round(rel_score_float * 100, 1)

                reason = (
                    f"Recommended because your assessment score in {comp_name} was {score_pct}%, "
                    f"identified as a {gap_val} priority skill gap. This course has a {relevance_pct}% domain "
                    f"relevance to this competency, resulting in a match score of {match_score}%."
                )

                gap_candidates.append({
                    "officer_id": assessment.officer_id,
                    "assessment_id": assessment.id,
                    "competency_id": gap.competency_id,
                    "course_id": course.id,
                    "priority": gap_priority,
                    "match_score": match_score,
                    "reason": reason,
                    "relevance_score": rel_score_float,
                })

            # Sort deterministically within gap
            gap_candidates.sort(
                key=lambda x: (
                    x["priority"],
                    -x["match_score"],
                    -x["relevance_score"],
                    x["course_id"],
                )
            )
            # Apply per-gap limit
            selected_for_gap = gap_candidates[: settings.MAX_RECOMMENDATIONS_PER_GAP]
            per_gap_candidates.extend(selected_for_gap)

        # 2. Global Deterministic Ordering and Active Cap
        per_gap_candidates.sort(
            key=lambda x: (
                x["priority"],
                -x["match_score"],
                -x["relevance_score"],
                x["course_id"],
            )
        )
        # Deduplicate candidates across gaps if a course was selected for multiple gaps
        seen_courses = set()
        deduped_candidates = []
        for cand in per_gap_candidates:
            if cand["course_id"] not in seen_courses:
                seen_courses.add(cand["course_id"])
                deduped_candidates.append(cand)

        # Slice to active limit
        target_active_candidates = deduped_candidates[: settings.MAX_TOTAL_ACTIVE_RECOMMENDATIONS]

        # 3. Idempotent Reconciliation preserving history (STARTED, COMPLETED, DISMISSED)
        existing_recs = (
            db.query(Recommendation)
            .filter(
                Recommendation.assessment_id == assessment_id,
                Recommendation.officer_id == assessment.officer_id,
            )
            .all()
        )

        existing_by_key = {(r.competency_id, r.course_id): r for r in existing_recs}
        dismissed_keys = {(r.competency_id, r.course_id) for r in existing_recs if r.status == RecommendationStatus.DISMISSED}
        engaged_keys = {(r.competency_id, r.course_id) for r in existing_recs if r.status in {RecommendationStatus.STARTED, RecommendationStatus.COMPLETED}}

        target_candidate_keys = set()
        for cand in target_active_candidates:
            key = (cand["competency_id"], cand["course_id"])
            target_candidate_keys.add(key)

            # If dismissed, respect dismissal
            if key in dismissed_keys:
                continue
            # If already engaged (STARTED or COMPLETED), preserve untouched
            if key in engaged_keys:
                continue

            existing_rec = existing_by_key.get(key)
            if existing_rec:
                if existing_rec.status == RecommendationStatus.RECOMMENDED:
                    # Refresh fields
                    existing_rec.priority = cand["priority"]
                    existing_rec.match_score = Decimal(str(cand["match_score"]))
                    existing_rec.reason = cand["reason"]
            else:
                new_rec = Recommendation(
                    officer_id=cand["officer_id"],
                    assessment_id=cand["assessment_id"],
                    competency_id=cand["competency_id"],
                    course_id=cand["course_id"],
                    priority=cand["priority"],
                    match_score=Decimal(str(cand["match_score"])),
                    reason=cand["reason"],
                    status=RecommendationStatus.RECOMMENDED,
                )
                db.add(new_rec)

        # Remove unstarted RECOMMENDED rows that fell out of the active selection
        for r in existing_recs:
            key = (r.competency_id, r.course_id)
            if r.status == RecommendationStatus.RECOMMENDED and key not in target_candidate_keys:
                db.delete(r)

        db.commit()

        # Query all current recommendations for response
        final_recs = (
            db.query(Recommendation)
            .filter(
                Recommendation.assessment_id == assessment_id,
                Recommendation.officer_id == assessment.officer_id,
            )
            .order_by(
                Recommendation.priority.asc(),
                Recommendation.match_score.desc(),
                Recommendation.id.asc(),
            )
            .all()
        )

        return [cls._build_response(r) for r in final_recs]

    @classmethod
    def list_assessment_recommendations(
        cls,
        db: Session,
        assessment_id: int,
        current_user: User,
    ) -> List[RecommendationResponse]:
        """Lists recommendations for a given assessment."""
        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assessment with ID {assessment_id} not found.",
            )

        user_role = current_user.role.name if current_user.role else ""
        if user_role == RoleName.OFFICER.value and assessment.officer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only view recommendations for your own assessments.",
            )
        if user_role == RoleName.SME.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="SME role is not authorized to inspect assessment recommendations.",
            )

        recs = (
            db.query(Recommendation)
            .filter(Recommendation.assessment_id == assessment_id)
            .order_by(
                Recommendation.priority.asc(),
                Recommendation.match_score.desc(),
                Recommendation.id.asc(),
            )
            .all()
        )
        return [cls._build_response(r) for r in recs]

    @classmethod
    def list_recommendations(
        cls,
        db: Session,
        current_user: User,
        assessment_id: Optional[int] = None,
        status_filter: Optional[RecommendationStatus] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> RecommendationListResponse:
        """Lists recommendations across assessments with filtering and RBAC enforcement."""
        user_role = current_user.role.name if current_user.role else ""
        if user_role == RoleName.SME.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="SME role is not authorized to inspect recommendations.",
            )

        query = db.query(Recommendation)
        if user_role == RoleName.OFFICER.value:
            query = query.filter(Recommendation.officer_id == current_user.id)

        if assessment_id:
            query = query.filter(Recommendation.assessment_id == assessment_id)
        if status_filter:
            query = query.filter(Recommendation.status == status_filter)

        total = query.count()
        recs = (
            query.order_by(
                Recommendation.priority.asc(),
                Recommendation.match_score.desc(),
                Recommendation.id.asc(),
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

        return RecommendationListResponse(
            total=total,
            items=[cls._build_response(r) for r in recs],
        )

    @classmethod
    def get_recommendation(
        cls,
        db: Session,
        recommendation_id: int,
        current_user: User,
    ) -> RecommendationResponse:
        """Fetch details of a single recommendation."""
        rec = db.query(Recommendation).filter(Recommendation.id == recommendation_id).first()
        if not rec:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Recommendation with ID {recommendation_id} not found.",
            )

        user_role = current_user.role.name if current_user.role else ""
        if user_role == RoleName.OFFICER.value and rec.officer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only view your own recommendations.",
            )
        if user_role == RoleName.SME.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="SME role is not authorized to inspect recommendations.",
            )

        return cls._build_response(rec)

    @classmethod
    def update_recommendation_status(
        cls,
        db: Session,
        recommendation_id: int,
        request: RecommendationStatusUpdateRequest,
        current_user: User,
    ) -> RecommendationResponse:
        """Enforces the strict status state machine for a recommendation."""
        rec = db.query(Recommendation).filter(Recommendation.id == recommendation_id).first()
        if not rec:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Recommendation with ID {recommendation_id} not found.",
            )

        user_role = current_user.role.name if current_user.role else ""
        if user_role == RoleName.OFFICER.value and rec.officer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only update your own recommendations.",
            )
        if user_role in {RoleName.TRAINER.value, RoleName.SME.value}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"{user_role} role is not authorized to update recommendation status.",
            )

        current_st = rec.status
        target_st = request.status

        # Validate state transition
        allowed_targets = ALLOWED_TRANSITIONS.get(current_st, set())
        if target_st not in allowed_targets:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status transition from {current_st.value} to {target_st.value}.",
            )

        rec.status = target_st
        db.commit()
        db.refresh(rec)
        logger.info(f"Recommendation {rec.id} transitioned from {current_st.value} to {target_st.value}")

        return cls._build_response(rec)

    @classmethod
    def _build_response(cls, rec: Recommendation) -> RecommendationResponse:
        """Helper to serialize Recommendation model into response schema with course and competency details."""
        course = rec.course
        comp = rec.competency

        return RecommendationResponse(
            id=rec.id,
            officer_id=rec.officer_id,
            assessment_id=rec.assessment_id,
            competency_id=rec.competency_id,
            competency_code=comp.code if comp else None,
            competency_name=comp.name if comp else None,
            course_id=rec.course_id,
            course_title=course.title if course else f"Course {rec.course_id}",
            course_url=course.course_url if course else None,
            course_provider=course.provider if course else None,
            course_duration_minutes=course.duration_minutes if course else None,
            course_difficulty=course.difficulty if course else None,
            priority=rec.priority,
            match_score=float(rec.match_score),
            reason=rec.reason,
            status=rec.status,
            created_at=rec.created_at,
        )
