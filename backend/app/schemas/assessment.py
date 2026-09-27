from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import AssessmentStatus, GapLevel, ProficiencyLevel, QuestionDifficulty


class AssessmentCreateRequest(BaseModel):
    """Payload to create and initialize a diagnostic assessment."""
    title: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=255,
        description="Optional assessment title. If omitted, defaults to a descriptive title.",
    )
    question_count: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Number of approved competency-tagged questions to assign (1-50).",
    )
    competency_id: Optional[int] = Field(
        default=None,
        description="Optional filter to select questions tagged with a specific competency.",
    )
    document_id: Optional[int] = Field(
        default=None,
        description="Optional filter to select questions originating from a specific document.",
    )
    officer_id: Optional[int] = Field(
        default=None,
        description="Target officer ID if initiated by Admin or Trainer. Ignored if called by an Officer.",
    )


class AssessmentQuestionResponse(BaseModel):
    """Officer-facing question representation during an active (IN_PROGRESS) assessment.
    
    Security Guarantee: Never exposes correct_option, explanation, or source chunk IDs.
    """
    id: int
    question_order: int
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    difficulty: QuestionDifficulty
    competency_id: Optional[int] = None
    competency_name: Optional[str] = None
    selected_option: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AnswerSubmission(BaseModel):
    """Individual question answer choice in a submission."""
    question_id: int = Field(..., description="ID of the assessment question.")
    selected_option: str = Field(..., description="Selected option ('A', 'B', 'C', or 'D').")

    @field_validator("selected_option")
    @classmethod
    def validate_option(cls, v: str) -> str:
        clean = v.strip().upper()
        if clean not in {"A", "B", "C", "D"}:
            raise ValueError("selected_option must be one of 'A', 'B', 'C', or 'D'")
        return clean


class AssessmentSubmitRequest(BaseModel):
    """Payload to atomically submit all answers for an assessment."""
    answers: List[AnswerSubmission] = Field(
        default_factory=list,
        description="List of answers for all assigned questions in the assessment.",
    )


class CompetencyResultResponse(BaseModel):
    """Competency-level proficiency outcome."""
    competency_id: int
    competency_code: Optional[str] = None
    competency_name: Optional[str] = None
    questions_attempted: int
    questions_correct: int
    score_percentage: float
    proficiency_level: ProficiencyLevel

    model_config = ConfigDict(from_attributes=True)


class SkillGapResponse(BaseModel):
    """Identified competency deficiency requiring training."""
    competency_id: int
    competency_code: Optional[str] = None
    competency_name: Optional[str] = None
    score_percentage: float
    gap_level: GapLevel

    model_config = ConfigDict(from_attributes=True)


class AssessmentQuestionDetailResponse(BaseModel):
    """Full question evaluation details unmasked only after assessment completion."""
    question_id: int
    question_order: int
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    selected_option: Optional[str] = None
    correct_option: str
    is_correct: bool
    explanation: Optional[str] = None
    source_page: Optional[int] = None
    source_chunk_id: Optional[int] = None
    competency_id: Optional[int] = None
    competency_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AssessmentResponse(BaseModel):
    """Assessment metadata and active state."""
    id: int
    officer_id: int
    title: str
    status: AssessmentStatus
    total_questions: int
    total_correct: int
    score_percentage: float
    started_at: datetime
    completed_at: Optional[datetime] = None
    questions: Optional[List[AssessmentQuestionResponse]] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("score_percentage", mode="before")
    @classmethod
    def convert_decimal(cls, v):
        if isinstance(v, Decimal):
            return float(v)
        return v


class AssessmentListResponse(BaseModel):
    """Paginated collection of assessments."""
    total: int
    items: List[AssessmentResponse]


class AssessmentDetailResponse(BaseModel):
    """Detailed view of an assessment including questions."""
    id: int
    officer_id: int
    title: str
    status: AssessmentStatus
    total_questions: int
    total_correct: int
    score_percentage: float
    started_at: datetime
    completed_at: Optional[datetime] = None
    questions: List[AssessmentQuestionResponse]

    model_config = ConfigDict(from_attributes=True)

    @field_validator("score_percentage", mode="before")
    @classmethod
    def convert_decimal(cls, v):
        if isinstance(v, Decimal):
            return float(v)
        return v


class AssessmentResultResponse(BaseModel):
    """Comprehensive evaluated assessment report with competency breakdown and skill gaps."""
    assessment_id: int
    officer_id: int
    title: str
    status: AssessmentStatus
    total_questions: int
    total_correct: int
    score_percentage: float
    started_at: datetime
    completed_at: Optional[datetime] = None
    competency_results: List[CompetencyResultResponse]
    skill_gaps: List[SkillGapResponse]
    questions: List[AssessmentQuestionDetailResponse]

    model_config = ConfigDict(from_attributes=True)

    @field_validator("score_percentage", mode="before")
    @classmethod
    def convert_decimal(cls, v):
        if isinstance(v, Decimal):
            return float(v)
        return v


# ============================================================================
# Phase 9: Reassessment & Closed Learning Loop Schemas
# ============================================================================

class ReassessmentCreateRequest(BaseModel):
    """Payload to initiate a targeted reassessment linked to a completed baseline assessment."""
    title: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=255,
        description="Optional custom title for the reassessment attempt. Defaults to canonical baseline reference format.",
    )
    question_count: Optional[int] = Field(
        default=None,
        ge=1,
        le=50,
        description="Optional number of approved questions to assign. Defaults to available gap-targeted questions.",
    )
    competency_ids: Optional[List[int]] = Field(
        default=None,
        description="Optional list of specific competency IDs to reassess. Defaults to all competencies with baseline skill gaps.",
    )


class LearningContextItem(BaseModel):
    """Correlated learning activity completed by the officer prior to reassessment."""
    course_id: int
    igot_course_id: Optional[str] = None
    course_title: str
    status: str
    correlation_note: str

    model_config = ConfigDict(from_attributes=True)


class CompetencyComparisonItem(BaseModel):
    """Detailed before-vs-after comparison for a single competency."""
    competency_id: int
    competency_code: Optional[str] = None
    competency_name: str
    baseline_score: float
    baseline_proficiency: str
    baseline_gap_level: Optional[str] = None
    reassessment_score: float
    reassessment_proficiency: str
    reassessment_gap_level: Optional[str] = None
    delta: float
    improvement_status: str  # IMPROVED, UNCHANGED, DECLINED
    gap_resolution_status: str  # RESOLVED, REDUCED, PERSISTENT, INCREASED, NO_GAP, NEW_GAP
    associated_learning: List[LearningContextItem] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ReassessmentComparisonResponse(BaseModel):
    """Holistic before-vs-after comparison evaluating the closed learning loop."""
    baseline_assessment_id: int
    baseline_title: str
    baseline_completed_at: Optional[datetime] = None
    baseline_overall_score: float
    reassessment_assessment_id: int
    reassessment_title: str
    reassessment_completed_at: Optional[datetime] = None
    reassessment_overall_score: float
    overall_delta: float
    overall_improvement_status: str  # IMPROVED, UNCHANGED, DECLINED
    loop_status: str  # LOOP_CLOSED, PARTIALLY_CLOSED, LOOP_OPEN
    competency_comparisons: List[CompetencyComparisonItem]
    declined_competency_ids: List[int] = Field(default_factory=list)
    summary_narrative: str

    model_config = ConfigDict(from_attributes=True)


class ReassessmentSummaryItem(BaseModel):
    """Summary of a single reassessment attempt linked to a baseline assessment."""
    id: int
    officer_id: int
    title: str
    status: AssessmentStatus
    total_questions: int
    total_correct: int
    score_percentage: float
    started_at: datetime
    completed_at: Optional[datetime] = None
    attempt_number: int

    model_config = ConfigDict(from_attributes=True)

    @field_validator("score_percentage", mode="before")
    @classmethod
    def convert_decimal(cls, v):
        if isinstance(v, Decimal):
            return float(v)
        return v


class ReassessmentListResponse(BaseModel):
    """Collection of reassessment attempts linked to a baseline assessment."""
    baseline_assessment_id: int
    total_attempts: int
    items: List[ReassessmentSummaryItem]

