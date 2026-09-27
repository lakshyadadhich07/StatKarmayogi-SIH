from datetime import datetime, timezone
from decimal import Decimal
import logging
import re
from typing import List, Optional, Set, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.core.config import settings
from app.models.answer import Answer
from app.models.assessment import Assessment
from app.models.assessment_question import AssessmentQuestion
from app.models.competency import Competency
from app.models.competency_result import CompetencyResult
from app.models.enums import AssessmentStatus, GapLevel, ProficiencyLevel, QuestionDifficulty, QuestionStatus, RecommendationStatus, RoleName
from app.models.question import Question
from app.models.recommendation import Recommendation
from app.models.skill_gap import SkillGap
from app.models.user import User
from app.schemas.assessment import (
    AssessmentDetailResponse,
    AssessmentQuestionResponse,
    CompetencyComparisonItem,
    LearningContextItem,
    ReassessmentComparisonResponse,
    ReassessmentCreateRequest,
    ReassessmentListResponse,
    ReassessmentSummaryItem,
)
from app.services.assessment_service import AssessmentService

logger = logging.getLogger(__name__)

# Canonical regex pattern for title-based baseline linkage (Zero Schema Changes)
REASSESSMENT_TITLE_PATTERN = re.compile(r"^Reassessment \[Baseline #(\d+)\]: (.+)$")


def format_reassessment_title(baseline_id: int, base_title: str) -> str:
    """Formats the canonical reassessment title encoding the baseline assessment ID."""
    return f"Reassessment [Baseline #{baseline_id}]: {base_title}"


def parse_baseline_id_from_title(title: Optional[str]) -> Optional[int]:
    """Extracts the linked baseline assessment ID from a canonical reassessment title.
    
    Returns:
        int: The baseline assessment ID if properly formatted.
        None: If title is empty, malformed, or not a reassessment title.
    """
    if not title:
        return None
    match = REASSESSMENT_TITLE_PATTERN.match(title.strip())
    return int(match.group(1)) if match else None


class ReassessmentService:
    """Service orchestrating targeted reassessment creation, longitudinal comparison, and closed learning loop evaluation."""

    SEVERITY_RANK = {
        GapLevel.HIGH: 3,
        GapLevel.MEDIUM: 2,
        GapLevel.LOW: 1,
    }

    @classmethod
    def create_reassessment(
        cls,
        db: Session,
        baseline_id: int,
        request: Optional[ReassessmentCreateRequest],
        current_user: User,
    ) -> AssessmentDetailResponse:
        """Creates a targeted reassessment linked to a completed baseline assessment.
        
        Validations:
        - Baseline must exist (404).
        - Caller must be OFFICER (owner of baseline) or ADMIN (403).
        - SME and TRAINER forbidden (403).
        - Baseline must be COMPLETED (400).
        - Baseline cannot itself be a reassessment (400).
        - Assigned questions target competencies where gaps were identified.
        """
        # 1. RBAC Check
        if current_user.role.name in {RoleName.SME.value, RoleName.TRAINER.value}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"{current_user.role.name} role is not authorized to create reassessments.",
            )

        # 2. Baseline Lookup & Validation
        baseline = db.query(Assessment).filter(Assessment.id == baseline_id).first()
        if not baseline:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Baseline assessment with ID {baseline_id} not found.",
            )

        if current_user.role.name == RoleName.OFFICER.value and baseline.officer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only create reassessments for your own baseline assessments.",
            )

        if baseline.status != AssessmentStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Baseline assessment must be completed before triggering a reassessment.",
            )

        # Disallow reassessing a reassessment (reassessments must link to an original baseline)
        if parse_baseline_id_from_title(baseline.title) is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot create a reassessment of another reassessment. Target must be an original baseline assessment.",
            )

        # 3. Determine Target Competencies
        if request and request.competency_ids:
            # Explicitly specified competencies
            comps = db.query(Competency).filter(Competency.id.in_(request.competency_ids)).all()
            if len(comps) != len(set(request.competency_ids)):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="One or more specified competencies not found.",
                )
            target_comp_ids = list(set(request.competency_ids))
        else:
            # Default to all competencies where baseline had skill gaps
            baseline_gaps = db.query(SkillGap).filter(SkillGap.assessment_id == baseline.id).all()
            target_comp_ids = [sg.competency_id for sg in baseline_gaps]

            # If baseline had no skill gaps, fallback to all evaluated competencies in baseline
            if not target_comp_ids:
                baseline_results = db.query(CompetencyResult).filter(CompetencyResult.assessment_id == baseline.id).all()
                target_comp_ids = [cr.competency_id for cr in baseline_results]

            if not target_comp_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Baseline assessment has no evaluated competencies or skill gaps to reassess.",
                )

        # 4. Question Selection (Approved, tagged with target competencies, deterministic order)
        query = (
            db.query(Question)
            .filter(
                Question.status == QuestionStatus.APPROVED,
                Question.competency_id.in_(target_comp_ids),
            )
            .order_by(Question.id.asc())
        )
        available_questions = query.all()

        if not available_questions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No approved questions available for the targeted competencies.",
            )

        if request and request.question_count:
            if len(available_questions) < request.question_count:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Insufficient approved competency-tagged questions available. "
                        f"Requested {request.question_count}, but only {len(available_questions)} found."
                    ),
                )
            selected_questions = available_questions[: request.question_count]
        else:
            desired = min(baseline.total_questions, len(available_questions)) if baseline.total_questions > 0 else min(10, len(available_questions))
            selected_questions = available_questions[:desired]

        # 5. Format Canonical Reassessment Title
        base_title = (request.title.strip() if request and request.title else baseline.title)
        reassessment_title = format_reassessment_title(baseline.id, base_title)

        # 6. Atomic Persistence
        try:
            reassessment = Assessment(
                officer_id=baseline.officer_id,
                title=reassessment_title,
                status=AssessmentStatus.IN_PROGRESS,
                total_questions=len(selected_questions),
                total_correct=0,
                score_percentage=Decimal("0.00"),
            )
            db.add(reassessment)
            db.flush()

            for idx, q in enumerate(selected_questions, start=1):
                aq = AssessmentQuestion(
                    assessment_id=reassessment.id,
                    question_id=q.id,
                    question_order=idx,
                )
                db.add(aq)

            db.commit()
            db.refresh(reassessment)
            logger.info(
                f"Reassessment {reassessment.id} successfully created for baseline {baseline.id} "
                f"(Officer {baseline.officer_id}) with {len(selected_questions)} questions."
            )
            return AssessmentService.get_assessment(db=db, assessment_id=reassessment.id, current_user=current_user)
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create reassessment for baseline {baseline.id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred while creating reassessment.",
            )

    @classmethod
    def get_reassessment_comparison(
        cls,
        db: Session,
        reassessment_id: int,
        baseline_id: Optional[int],
        current_user: User,
    ) -> ReassessmentComparisonResponse:
        """Computes deterministic before/after comparison between baseline and reassessment.
        
        Enforces strict Macro Closed-Loop State Precedence:
        1. LOOP_CLOSED: Every baseline gap reached >= 80.0% (ADVANCED, no baseline skill gap remains unresolved).
        2. PARTIALLY_CLOSED: At least one baseline gap is RESOLVED or REDUCED, and at least one baseline deficiency remains unresolved.
           (A decline in another competency does NOT override PARTIALLY_CLOSED).
        3. LOOP_OPEN: Zero baseline gaps improved/reduced, or no baseline gaps qualify for partial closure, and state is not LOOP_CLOSED or PARTIALLY_CLOSED.
        
        Separately reports individual competency outcomes and lists declined competencies.
        """
        # 1. RBAC Check
        if current_user.role.name == RoleName.SME.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. SME role cannot inspect comparison reports.",
            )

        # 2. Reassessment Lookup & Validation
        reassessment = db.query(Assessment).filter(Assessment.id == reassessment_id).first()
        if not reassessment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Reassessment with ID {reassessment_id} not found.",
            )

        if current_user.role.name == RoleName.OFFICER.value and reassessment.officer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only view comparisons for your own assessments.",
            )

        if reassessment.status != AssessmentStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reassessment is still in progress. Comparison is only available after completion.",
            )

        # 3. Resolve Baseline Linkage
        parsed_baseline_id = parse_baseline_id_from_title(reassessment.title)
        if baseline_id is not None:
            if parsed_baseline_id is not None and baseline_id != parsed_baseline_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Specified baseline_id ({baseline_id}) does not match the reassessment linkage ({parsed_baseline_id}).",
                )
            target_baseline_id = baseline_id
        else:
            if parsed_baseline_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Malformed linkage: Assessment {reassessment_id} does not contain valid baseline linkage in title and no baseline_id query parameter was provided.",
                )
            target_baseline_id = parsed_baseline_id

        # Self-comparison guard
        if target_baseline_id == reassessment.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot compare an assessment against itself.",
            )

        # 4. Baseline Lookup & Validation
        baseline = db.query(Assessment).filter(Assessment.id == target_baseline_id).first()
        if not baseline:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Baseline assessment with ID {target_baseline_id} not found.",
            )

        if baseline.status != AssessmentStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Baseline assessment must be completed.",
            )

        if baseline.officer_id != reassessment.officer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Baseline assessment belongs to a different officer.",
            )

        # 5. Load Results & Gaps
        b_crs = db.query(CompetencyResult).filter(CompetencyResult.assessment_id == baseline.id).all()
        b_cr_map = {cr.competency_id: cr for cr in b_crs}
        b_sgs = db.query(SkillGap).filter(SkillGap.assessment_id == baseline.id).all()
        b_sg_map = {sg.competency_id: sg for sg in b_sgs}

        r_crs = db.query(CompetencyResult).filter(CompetencyResult.assessment_id == reassessment.id).all()
        r_cr_map = {cr.competency_id: cr for cr in r_crs}
        r_sgs = db.query(SkillGap).filter(SkillGap.assessment_id == reassessment.id).all()
        r_sg_map = {sg.competency_id: sg for sg in r_sgs}

        # 6. Load Preceding Learning Activities (Non-causal Educational Context)
        recs = (
            db.query(Recommendation)
            .filter(
                Recommendation.officer_id == baseline.officer_id,
                Recommendation.status.in_([RecommendationStatus.COMPLETED, RecommendationStatus.STARTED]),
            )
            .all()
        )
        rec_by_comp: dict[int, list[Recommendation]] = {}
        for r in recs:
            rec_by_comp.setdefault(r.competency_id, []).append(r)

        # 7. Evaluate Macro Closed-Loop State
        baseline_gap_comp_ids = set(b_sg_map.keys())

        def is_resolved(cid: int) -> bool:
            return cid in r_cr_map and float(r_cr_map[cid].score_percentage) >= settings.ADVANCED_THRESHOLD

        def is_reduced(cid: int) -> bool:
            if cid not in b_sg_map:
                return False
            bg = b_sg_map[cid].gap_level
            rg = r_sg_map[cid].gap_level if cid in r_sg_map else None
            if rg is not None and cls.SEVERITY_RANK.get(rg, 0) < cls.SEVERITY_RANK.get(bg, 0):
                return True
            return False

        # Macro Precedence Rule 1: LOOP_CLOSED
        # Every baseline gap reached >= 80.0% (ADVANCED, no baseline skill gap remains unresolved)
        if len(baseline_gap_comp_ids) > 0 and all(is_resolved(cid) for cid in baseline_gap_comp_ids):
            loop_status = "LOOP_CLOSED"
        # Macro Precedence Rule 2: PARTIALLY_CLOSED
        # At least one baseline gap is RESOLVED or REDUCED, and at least one baseline deficiency remains unresolved.
        # (A decline in another competency does NOT override PARTIALLY_CLOSED).
        elif any(is_resolved(cid) or is_reduced(cid) for cid in baseline_gap_comp_ids) and any(not is_resolved(cid) for cid in baseline_gap_comp_ids):
            loop_status = "PARTIALLY_CLOSED"
        # Macro Precedence Rule 3: LOOP_OPEN
        # Zero baseline gaps improved/reduced, or no baseline gaps qualify for partial closure, and state is not LOOP_CLOSED or PARTIALLY_CLOSED.
        else:
            loop_status = "LOOP_OPEN"

        # 8. Build Granular Competency Comparisons
        # Evaluate all competencies tested in reassessment
        comp_ids_to_compare = sorted(list(r_cr_map.keys()))
        competency_comparisons: List[CompetencyComparisonItem] = []
        declined_competency_ids: List[int] = []

        for cid in comp_ids_to_compare:
            r_cr = r_cr_map[cid]
            r_score = float(r_cr.score_percentage)
            r_prof = r_cr.proficiency_level.value
            r_gap = r_sg_map[cid].gap_level.value if cid in r_sg_map else None

            if cid in b_cr_map:
                b_cr = b_cr_map[cid]
                b_score = float(b_cr.score_percentage)
                b_prof = b_cr.proficiency_level.value
                b_gap = b_sg_map[cid].gap_level.value if cid in b_sg_map else None
                comp_name = b_cr.competency.name if b_cr.competency else f"Competency {cid}"
                comp_code = b_cr.competency.code if b_cr.competency else f"COMP-{cid}"
            else:
                b_score = 0.0
                b_prof = ProficiencyLevel.BEGINNER.value
                b_gap = GapLevel.HIGH.value
                comp_name = r_cr.competency.name if r_cr.competency else f"Competency {cid}"
                comp_code = r_cr.competency.code if r_cr.competency else f"COMP-{cid}"

            delta = round(r_score - b_score, 2)
            if delta > 0.0:
                imp_status = "IMPROVED"
            elif delta < 0.0:
                imp_status = "DECLINED"
                declined_competency_ids.append(cid)
            else:
                imp_status = "UNCHANGED"

            # Resolution status per competency
            if cid in b_sg_map:
                if r_score >= settings.ADVANCED_THRESHOLD:
                    gap_res = "RESOLVED"
                else:
                    bg_rank = cls.SEVERITY_RANK.get(b_sg_map[cid].gap_level, 0)
                    rg_rank = cls.SEVERITY_RANK.get(r_sg_map[cid].gap_level, 0) if cid in r_sg_map else 0
                    if rg_rank < bg_rank:
                        gap_res = "REDUCED"
                    elif rg_rank == bg_rank:
                        gap_res = "PERSISTENT"
                    else:
                        gap_res = "INCREASED"
            else:
                # Competency had NO gap in baseline
                if r_score >= settings.ADVANCED_THRESHOLD:
                    gap_res = "NO_GAP"
                else:
                    gap_res = "NEW_GAP"

            # Compile associated learning with non-causal developmental attribution
            learning_items: List[LearningContextItem] = []
            for rec in rec_by_comp.get(cid, []):
                course_title = rec.course.title if rec.course else f"Course {rec.course_id}"
                igot_id = rec.course.igot_course_id if rec.course else None
                delta_str = f"+{delta}" if delta >= 0 else f"{delta}"

                if rec.status == RecommendationStatus.COMPLETED:
                    note = (
                        f"Officer completed course '{course_title}' prior to reassessment. "
                        f"Competency score changed from {b_score}% to {r_score}% ({delta_str}%). "
                        f"This learning activity is documented as developmental context and educational correlation, "
                        f"not formal causal proof."
                    )
                else:
                    note = (
                        f"Officer started course '{course_title}' prior to reassessment. "
                        f"This learning activity is documented as in-progress developmental context."
                    )

                learning_items.append(
                    LearningContextItem(
                        course_id=rec.course_id,
                        igot_course_id=igot_id,
                        course_title=course_title,
                        status=rec.status.value,
                        correlation_note=note,
                    )
                )

            competency_comparisons.append(
                CompetencyComparisonItem(
                    competency_id=cid,
                    competency_code=comp_code,
                    competency_name=comp_name,
                    baseline_score=b_score,
                    baseline_proficiency=b_prof,
                    baseline_gap_level=b_gap,
                    reassessment_score=r_score,
                    reassessment_proficiency=r_prof,
                    reassessment_gap_level=r_gap,
                    delta=delta,
                    improvement_status=imp_status,
                    gap_resolution_status=gap_res,
                    associated_learning=learning_items,
                )
            )

        # 9. Overall Scores & Narrative
        b_overall = float(baseline.score_percentage)
        r_overall = float(reassessment.score_percentage)
        overall_delta = round(r_overall - b_overall, 2)
        if overall_delta > 0.0:
            overall_imp = "IMPROVED"
        elif overall_delta < 0.0:
            overall_imp = "DECLINED"
        else:
            overall_imp = "UNCHANGED"

        resolved_count = sum(1 for cid in baseline_gap_comp_ids if is_resolved(cid))
        summary_narrative = (
            f"Reassessment #{reassessment.id} for baseline #{baseline.id} demonstrates an overall score change "
            f"of {overall_delta:+.2f}% (from {b_overall}% to {r_overall}%). "
            f"Closed-loop evaluation status is {loop_status} with {resolved_count} of {len(baseline_gap_comp_ids)} "
            f"baseline skill gaps resolved. All preceding learning activities are documented as developmental context "
            f"and educational correlation, not formal causal proof."
        )

        return ReassessmentComparisonResponse(
            baseline_assessment_id=baseline.id,
            baseline_title=baseline.title,
            baseline_completed_at=baseline.completed_at,
            baseline_overall_score=b_overall,
            reassessment_assessment_id=reassessment.id,
            reassessment_title=reassessment.title,
            reassessment_completed_at=reassessment.completed_at,
            reassessment_overall_score=r_overall,
            overall_delta=overall_delta,
            overall_improvement_status=overall_imp,
            loop_status=loop_status,
            competency_comparisons=competency_comparisons,
            declined_competency_ids=declined_competency_ids,
            summary_narrative=summary_narrative,
        )

    @classmethod
    def list_reassessments_for_baseline(
        cls,
        db: Session,
        baseline_id: int,
        current_user: User,
    ) -> ReassessmentListResponse:
        """Lists all sequential reassessment attempts linked to a specific baseline assessment."""
        # 1. RBAC Check
        if current_user.role.name == RoleName.SME.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. SME role cannot inspect reassessments.",
            )

        # 2. Baseline Lookup
        baseline = db.query(Assessment).filter(Assessment.id == baseline_id).first()
        if not baseline:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Baseline assessment with ID {baseline_id} not found.",
            )

        if current_user.role.name == RoleName.OFFICER.value and baseline.officer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only view reassessments for your own baseline assessments.",
            )

        # 3. Query Sequential Attempts (Deterministic Ordering)
        prefix = f"Reassessment [Baseline #{baseline_id}]:%"
        attempts = (
            db.query(Assessment)
            .filter(
                Assessment.officer_id == baseline.officer_id,
                Assessment.title.like(prefix),
            )
            .order_by(Assessment.started_at.asc(), Assessment.id.asc())
            .all()
        )

        items = [
            ReassessmentSummaryItem(
                id=a.id,
                officer_id=a.officer_id,
                title=a.title,
                status=a.status,
                total_questions=a.total_questions,
                total_correct=a.total_correct,
                score_percentage=float(a.score_percentage),
                started_at=a.started_at,
                completed_at=a.completed_at,
                attempt_number=idx + 1,
            )
            for idx, a in enumerate(attempts)
        ]

        return ReassessmentListResponse(
            baseline_assessment_id=baseline.id,
            total_attempts=len(items),
            items=items,
        )
