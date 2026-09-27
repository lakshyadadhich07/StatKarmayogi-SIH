from datetime import datetime, timezone
from decimal import Decimal
import logging
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.core.config import settings
from app.models.answer import Answer
from app.models.assessment import Assessment
from app.models.assessment_question import AssessmentQuestion
from app.models.competency import Competency
from app.models.competency_result import CompetencyResult
from app.models.document import Document
from app.models.enums import AssessmentStatus, GapLevel, ProficiencyLevel, QuestionStatus, RoleName
from app.models.question import Question
from app.models.skill_gap import SkillGap
from app.models.user import User
from app.schemas.assessment import (
    AssessmentCreateRequest,
    AssessmentDetailResponse,
    AssessmentQuestionDetailResponse,
    AssessmentQuestionResponse,
    AssessmentResponse,
    AssessmentResultResponse,
    AssessmentSubmitRequest,
    CompetencyResultResponse,
    SkillGapResponse,
)

logger = logging.getLogger(__name__)


class AssessmentService:
    """Service orchestrating assessment creation, question assignment, scoring, and skill gap identification."""

    @staticmethod
    def calculate_proficiency_level(score_percentage: float) -> ProficiencyLevel:
        """Determines proficiency level based on configurable prototype thresholds.
        
        Note: These are configurable prototype scoring thresholds and are not presented
        as official MoSPI competency thresholds.
        """
        if score_percentage >= settings.ADVANCED_THRESHOLD:
            return ProficiencyLevel.ADVANCED
        elif score_percentage >= settings.PROFICIENT_THRESHOLD:
            return ProficiencyLevel.PROFICIENT
        elif score_percentage >= settings.DEVELOPING_THRESHOLD:
            return ProficiencyLevel.DEVELOPING
        else:
            return ProficiencyLevel.BEGINNER

    @staticmethod
    def calculate_gap_level(score_percentage: float) -> Optional[GapLevel]:
        """Maps proficiency score to corresponding skill-gap severity.
        
        Note: These are configurable prototype scoring thresholds and are not presented
        as official MoSPI competency thresholds.
        - Score < DEVELOPING_THRESHOLD -> HIGH gap
        - Score < PROFICIENT_THRESHOLD -> MEDIUM gap
        - Score < ADVANCED_THRESHOLD -> LOW gap
        - Score >= ADVANCED_THRESHOLD -> None (Mastery achieved, no skill gap)
        """
        if score_percentage < settings.DEVELOPING_THRESHOLD:
            return GapLevel.HIGH
        elif score_percentage < settings.PROFICIENT_THRESHOLD:
            return GapLevel.MEDIUM
        elif score_percentage < settings.ADVANCED_THRESHOLD:
            return GapLevel.LOW
        else:
            return None

    @classmethod
    def create_assessment(
        cls,
        db: Session,
        request: AssessmentCreateRequest,
        current_user: User,
    ) -> Assessment:
        """Creates a diagnostic assessment with deterministically assigned APPROVED competency questions."""
        # 1. Enforce RBAC & Resolve Target Officer
        if current_user.role.name in {RoleName.SME.value, RoleName.TRAINER.value}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"{current_user.role.name} role is not authorized to create assessments.",
            )

        if current_user.role.name == RoleName.OFFICER.value:
            target_officer_id = current_user.id
        elif current_user.role.name == RoleName.ADMIN.value:
            if request.officer_id:
                target_user = db.query(User).filter(User.id == request.officer_id).first()
                if not target_user:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Target officer with ID {request.officer_id} not found.",
                    )
                target_officer_id = request.officer_id
            else:
                target_officer_id = current_user.id
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Role not authorized to create assessments.",
            )

        # 2. Validate Optional Filters
        if request.competency_id:
            comp = db.query(Competency).filter(Competency.id == request.competency_id).first()
            if not comp:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Competency with ID {request.competency_id} not found.",
                )

        if request.document_id:
            doc = db.query(Document).filter(Document.id == request.document_id).first()
            if not doc:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Document with ID {request.document_id} not found.",
                )

        # 3. Deterministic Question Selection (Approved & Competency-tagged only)
        query = db.query(Question).filter(
            Question.status == QuestionStatus.APPROVED,
            Question.competency_id.isnot(None),
        )

        if request.competency_id:
            query = query.filter(Question.competency_id == request.competency_id)
        if request.document_id:
            query = query.filter(Question.document_id == request.document_id)

        # Deterministic database ordering: ORDER BY questions.id ASC
        selected_questions = query.order_by(Question.id.asc()).limit(request.question_count).all()

        if len(selected_questions) < request.question_count:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Insufficient approved competency-tagged questions available for this assessment. "
                    f"Requested {request.question_count}, but only {len(selected_questions)} found."
                ),
            )

        # 4. Atomic Transaction Persistence
        title = request.title or f"MoSPI Competency Diagnostic Assessment - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}"

        try:
            assessment = Assessment(
                officer_id=target_officer_id,
                title=title,
                status=AssessmentStatus.IN_PROGRESS,
                total_questions=len(selected_questions),
                total_correct=0,
                score_percentage=Decimal("0.00"),
            )
            db.add(assessment)
            db.flush()

            for idx, q in enumerate(selected_questions, start=1):
                aq = AssessmentQuestion(
                    assessment_id=assessment.id,
                    question_id=q.id,
                    question_order=idx,
                )
                db.add(aq)

            db.commit()
            db.refresh(assessment)
            logger.info(
                f"Assessment {assessment.id} created for officer {target_officer_id} "
                f"with {len(selected_questions)} approved questions."
            )
            return assessment
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create assessment: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred while creating assessment.",
            )

    @classmethod
    def get_assessment(
        cls,
        db: Session,
        assessment_id: int,
        current_user: User,
    ) -> AssessmentDetailResponse:
        """Retrieves assessment details with strict answer key masking while IN_PROGRESS."""
        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assessment with ID {assessment_id} not found.",
            )

        # Enforce RBAC / Ownership
        if current_user.role.name == RoleName.OFFICER.value and assessment.officer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only view your own assessments.",
            )
        if current_user.role.name == RoleName.SME.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. SME role cannot inspect assessments.",
            )

        # Fetch questions preserving deterministic order
        assigned = (
            db.query(AssessmentQuestion)
            .filter(AssessmentQuestion.assessment_id == assessment_id)
            .order_by(AssessmentQuestion.question_order.asc())
            .all()
        )

        # Existing answers if any
        answers_map = {
            a.question_id: a.selected_option
            for a in db.query(Answer).filter(Answer.assessment_id == assessment_id).all()
        }

        # Safe masked question items (NEVER expose correct_option, explanation, or source chunk)
        safe_questions: List[AssessmentQuestionResponse] = []
        for aq in assigned:
            q = aq.question
            safe_questions.append(
                AssessmentQuestionResponse(
                    id=q.id,
                    question_order=aq.question_order,
                    question_text=q.question_text,
                    option_a=q.option_a,
                    option_b=q.option_b,
                    option_c=q.option_c,
                    option_d=q.option_d,
                    difficulty=q.difficulty,
                    competency_id=q.competency_id,
                    competency_name=q.competency.name if q.competency else None,
                    selected_option=answers_map.get(q.id),
                )
            )

        return AssessmentDetailResponse(
            id=assessment.id,
            officer_id=assessment.officer_id,
            title=assessment.title,
            status=assessment.status,
            total_questions=assessment.total_questions,
            total_correct=assessment.total_correct,
            score_percentage=float(assessment.score_percentage),
            started_at=assessment.started_at,
            completed_at=assessment.completed_at,
            questions=safe_questions,
        )

    @classmethod
    def submit_assessment(
        cls,
        db: Session,
        assessment_id: int,
        request: AssessmentSubmitRequest,
        current_user: User,
    ) -> AssessmentResultResponse:
        """Atomically evaluates submitted answers, computes deterministic scores, and persists competency results & skill gaps."""
        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assessment with ID {assessment_id} not found.",
            )

        # Enforce Ownership: only the officer who owns the assessment can submit it
        if current_user.role.name == RoleName.OFFICER.value and assessment.officer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only submit your own assessment.",
            )
        if current_user.role.name in {RoleName.TRAINER.value, RoleName.SME.value}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Trainers and SMEs are not authorized to submit assessments.",
            )
        if current_user.role.name == RoleName.ADMIN.value and current_user.id != assessment.officer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Administrators cannot submit an assessment on behalf of another officer.",
            )

        # Check status: completed assessments cannot be resubmitted
        if assessment.status == AssessmentStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assessment has already been completed and cannot be resubmitted.",
            )

        # Load assigned questions
        assigned_questions = (
            db.query(AssessmentQuestion)
            .filter(AssessmentQuestion.assessment_id == assessment_id)
            .order_by(AssessmentQuestion.question_order.asc())
            .all()
        )
        assigned_q_ids = {aq.question_id for aq in assigned_questions}
        assigned_q_order_map = {aq.question_id: aq.question_order for aq in assigned_questions}

        # Validate answers:
        if not request.answers or len(request.answers) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Submission cannot be empty. All assigned assessment questions must be answered.",
            )

        submitted_q_ids = [a.question_id for a in request.answers]
        if len(submitted_q_ids) != len(set(submitted_q_ids)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Duplicate answers submitted for the same question.",
            )

        submitted_set = set(submitted_q_ids)
        # Check for unassigned questions
        if not submitted_set.issubset(assigned_q_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Submitted answers contain question IDs not assigned to this assessment.",
            )

        # Check all questions must be answered
        if submitted_set != assigned_q_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="All assigned assessment questions must be answered before submission.",
            )

        # Load question entities
        questions = db.query(Question).filter(Question.id.in_(assigned_q_ids)).all()
        q_map = {q.id: q for q in questions}

        # Single Atomic Database Transaction
        try:
            total_correct = 0
            evaluated_items: List[AssessmentQuestionDetailResponse] = []
            competency_scores = {}  # cid -> {"total": int, "correct": int, "comp": Competency}

            for ans_sub in request.answers:
                q = q_map[ans_sub.question_id]
                is_correct = (ans_sub.selected_option.upper() == q.correct_option.upper())
                if is_correct:
                    total_correct += 1

                # Upsert into answers
                existing_ans = (
                    db.query(Answer)
                    .filter(Answer.assessment_id == assessment.id, Answer.question_id == q.id)
                    .first()
                )
                if existing_ans:
                    existing_ans.selected_option = ans_sub.selected_option.upper()
                    existing_ans.is_correct = is_correct
                    existing_ans.answered_at = func.now()
                else:
                    new_ans = Answer(
                        assessment_id=assessment.id,
                        question_id=q.id,
                        selected_option=ans_sub.selected_option.upper(),
                        is_correct=is_correct,
                    )
                    db.add(new_ans)

                # Group by competency
                cid = q.competency_id
                if cid not in competency_scores:
                    competency_scores[cid] = {"total": 0, "correct": 0, "comp": q.competency}
                competency_scores[cid]["total"] += 1
                if is_correct:
                    competency_scores[cid]["correct"] += 1

                evaluated_items.append(
                    AssessmentQuestionDetailResponse(
                        question_id=q.id,
                        question_order=assigned_q_order_map[q.id],
                        question_text=q.question_text,
                        option_a=q.option_a,
                        option_b=q.option_b,
                        option_c=q.option_c,
                        option_d=q.option_d,
                        selected_option=ans_sub.selected_option.upper(),
                        correct_option=q.correct_option,
                        is_correct=is_correct,
                        explanation=q.explanation,
                        source_page=q.source_page,
                        source_chunk_id=q.source_chunk_id,
                        competency_id=cid,
                        competency_name=q.competency.name if q.competency else None,
                    )
                )

            # Sort detailed question items by assigned question_order
            evaluated_items.sort(key=lambda item: item.question_order)

            # Overall Score Calculation
            total_questions = len(assigned_questions)
            overall_score = round((total_correct / total_questions) * 100, 2) if total_questions > 0 else 0.0
            assessment.total_questions = total_questions
            assessment.total_correct = total_correct
            assessment.score_percentage = Decimal(str(overall_score))
            assessment.status = AssessmentStatus.COMPLETED
            assessment.completed_at = datetime.now(timezone.utc)

            # Delete existing competency_results and skill_gaps if any before creating (idempotency guard)
            db.query(CompetencyResult).filter(CompetencyResult.assessment_id == assessment.id).delete()
            db.query(SkillGap).filter(SkillGap.assessment_id == assessment.id).delete()

            # Competency-Level Scoring & Skill Gap Identification
            comp_result_responses: List[CompetencyResultResponse] = []
            skill_gap_responses: List[SkillGapResponse] = []

            for cid, data in sorted(competency_scores.items(), key=lambda x: x[0]):
                comp_total = data["total"]
                comp_correct = data["correct"]
                comp_pct = round((comp_correct / comp_total) * 100, 2) if comp_total > 0 else 0.0
                prof_level = cls.calculate_proficiency_level(comp_pct)

                cr = CompetencyResult(
                    assessment_id=assessment.id,
                    competency_id=cid,
                    questions_attempted=comp_total,
                    questions_correct=comp_correct,
                    score_percentage=Decimal(str(comp_pct)),
                    proficiency_level=prof_level,
                )
                db.add(cr)

                comp_name = data["comp"].name if data["comp"] else f"Competency {cid}"
                comp_code = data["comp"].code if data["comp"] else f"COMP-{cid}"
                comp_result_responses.append(
                    CompetencyResultResponse(
                        competency_id=cid,
                        competency_code=comp_code,
                        competency_name=comp_name,
                        questions_attempted=comp_total,
                        questions_correct=comp_correct,
                        score_percentage=comp_pct,
                        proficiency_level=prof_level,
                    )
                )

                # Skill Gap Identification
                gap_lvl = cls.calculate_gap_level(comp_pct)
                if gap_lvl is not None:
                    sg = SkillGap(
                        assessment_id=assessment.id,
                        competency_id=cid,
                        score_percentage=Decimal(str(comp_pct)),
                        gap_level=gap_lvl,
                    )
                    db.add(sg)
                    skill_gap_responses.append(
                        SkillGapResponse(
                            competency_id=cid,
                            competency_code=comp_code,
                            competency_name=comp_name,
                            score_percentage=comp_pct,
                            gap_level=gap_lvl,
                        )
                    )

            # Atomic commit
            db.commit()
            db.refresh(assessment)
            logger.info(
                f"Assessment {assessment.id} successfully submitted and evaluated: "
                f"Score={overall_score}%, Competencies={len(comp_result_responses)}, Gaps={len(skill_gap_responses)}"
            )

            # Phase 8: Safe automatic recommendation generation hook
            try:
                from app.services.recommendation_service import RecommendationService
                RecommendationService.generate_recommendations(
                    db=db,
                    assessment_id=assessment.id,
                    current_user=current_user,
                )
            except Exception as rec_err:
                logger.error(
                    f"Automatic recommendation generation failed for assessment {assessment.id}: {rec_err}",
                    exc_info=True,
                )
                # Intentionally isolated: Assessment remains COMPLETED!
                # Officer/Admin can manually regenerate via POST /api/v1/assessments/{id}/recommendations

            return AssessmentResultResponse(
                assessment_id=assessment.id,
                officer_id=assessment.officer_id,
                title=assessment.title,
                status=assessment.status,
                total_questions=total_questions,
                total_correct=total_correct,
                score_percentage=overall_score,
                started_at=assessment.started_at,
                completed_at=assessment.completed_at,
                competency_results=comp_result_responses,
                skill_gaps=skill_gap_responses,
                questions=evaluated_items,
            )
        except Exception as e:
            db.rollback()
            logger.error(f"Atomic submission failed for assessment {assessment_id}: {e}", exc_info=True)
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred during assessment evaluation.",
            )

    @classmethod
    def get_assessment_result(
        cls,
        db: Session,
        assessment_id: int,
        current_user: User,
    ) -> AssessmentResultResponse:
        """Retrieves evaluated assessment outcome, competency profile, and identified skill gaps."""
        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assessment with ID {assessment_id} not found.",
            )

        # Check completion
        if assessment.status != AssessmentStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assessment is still in progress. Results are only available after submission.",
            )

        # Enforce RBAC
        if current_user.role.name == RoleName.OFFICER.value and assessment.officer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only view results of your own assessments.",
            )
        if current_user.role.name == RoleName.SME.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. SME role cannot inspect assessment results.",
            )

        # Load competency results
        crs = (
            db.query(CompetencyResult)
            .filter(CompetencyResult.assessment_id == assessment_id)
            .order_by(CompetencyResult.competency_id.asc())
            .all()
        )
        comp_result_responses = [
            CompetencyResultResponse(
                competency_id=cr.competency_id,
                competency_code=cr.competency.code if cr.competency else f"COMP-{cr.competency_id}",
                competency_name=cr.competency.name if cr.competency else f"Competency {cr.competency_id}",
                questions_attempted=cr.questions_attempted,
                questions_correct=cr.questions_correct,
                score_percentage=float(cr.score_percentage),
                proficiency_level=cr.proficiency_level,
            )
            for cr in crs
        ]

        # Load skill gaps
        sgs = (
            db.query(SkillGap)
            .filter(SkillGap.assessment_id == assessment_id)
            .order_by(SkillGap.competency_id.asc())
            .all()
        )
        skill_gap_responses = [
            SkillGapResponse(
                competency_id=sg.competency_id,
                competency_code=sg.competency.code if sg.competency else f"COMP-{sg.competency_id}",
                competency_name=sg.competency.name if sg.competency else f"Competency {sg.competency_id}",
                score_percentage=float(sg.score_percentage),
                gap_level=sg.gap_level,
            )
            for sg in sgs
        ]

        # Load detailed questions and answers
        assigned = (
            db.query(AssessmentQuestion)
            .filter(AssessmentQuestion.assessment_id == assessment_id)
            .order_by(AssessmentQuestion.question_order.asc())
            .all()
        )
        answers_map = {
            a.question_id: a
            for a in db.query(Answer).filter(Answer.assessment_id == assessment_id).all()
        }

        evaluated_items: List[AssessmentQuestionDetailResponse] = []
        for aq in assigned:
            q = aq.question
            ans = answers_map.get(q.id)
            evaluated_items.append(
                AssessmentQuestionDetailResponse(
                    question_id=q.id,
                    question_order=aq.question_order,
                    question_text=q.question_text,
                    option_a=q.option_a,
                    option_b=q.option_b,
                    option_c=q.option_c,
                    option_d=q.option_d,
                    selected_option=ans.selected_option if ans else None,
                    correct_option=q.correct_option,
                    is_correct=ans.is_correct if ans else False,
                    explanation=q.explanation,
                    source_page=q.source_page,
                    source_chunk_id=q.source_chunk_id,
                    competency_id=q.competency_id,
                    competency_name=q.competency.name if q.competency else None,
                )
            )

        return AssessmentResultResponse(
            assessment_id=assessment.id,
            officer_id=assessment.officer_id,
            title=assessment.title,
            status=assessment.status,
            total_questions=assessment.total_questions,
            total_correct=assessment.total_correct,
            score_percentage=float(assessment.score_percentage),
            started_at=assessment.started_at,
            completed_at=assessment.completed_at,
            competency_results=comp_result_responses,
            skill_gaps=skill_gap_responses,
            questions=evaluated_items,
        )

    @classmethod
    def list_assessments(
        cls,
        db: Session,
        current_user: User,
        status_filter: Optional[AssessmentStatus] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Assessment], int]:
        """Lists assessments according to RBAC ownership rules."""
        if current_user.role.name == RoleName.SME.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. SME role cannot list assessments.",
            )

        query = db.query(Assessment)
        if current_user.role.name == RoleName.OFFICER.value:
            query = query.filter(Assessment.officer_id == current_user.id)

        if status_filter:
            query = query.filter(Assessment.status == status_filter)

        total = query.count()
        items = query.order_by(Assessment.id.desc()).offset(skip).limit(limit).all()
        return items, total
