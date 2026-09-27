from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import QuestionDifficulty, QuestionStatus, ReviewAction


class MCQGenerationItem(BaseModel):
    """Schema enforced on Mistral LLM structured output for a single MCQ item."""

    source_chunk_id: int = Field(
        ...,
        description="The exact integer CHUNK ID number from which this question was derived, matching one of the provided chunks in context.",
    )
    question_text: str = Field(
        ...,
        description="The multiple choice question prompt, ending with a question mark.",
    )
    option_a: str = Field(..., description="Option A text.")
    option_b: str = Field(..., description="Option B text.")
    option_c: str = Field(..., description="Option C text.")
    option_d: str = Field(..., description="Option D text.")
    correct_option: Literal["A", "B", "C", "D"] = Field(
        ...,
        description="The single correct answer key: 'A', 'B', 'C', or 'D'.",
    )
    difficulty: QuestionDifficulty = Field(
        default=QuestionDifficulty.MEDIUM,
        description="Difficulty level of the question: EASY, MEDIUM, or HARD.",
    )
    explanation: str = Field(
        ...,
        description="Educational explanation justifying the correct answer using facts from the source text.",
    )


class MCQGenerationBatch(BaseModel):
    """Container schema for structured LLM response batch."""

    questions: List[MCQGenerationItem] = Field(
        default_factory=list,
        description="List of multiple choice questions generated strictly from the provided source context.",
    )


class QuestionGenerateRequest(BaseModel):
    """Request payload for triggering MCQ generation for a processed document."""

    document_id: int = Field(
        ...,
        description="The ID of the processed document to generate questions from.",
    )
    num_questions: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of MCQs to generate (minimum 1, maximum 20).",
    )
    difficulty: Optional[QuestionDifficulty] = Field(
        default=None,
        description="Optional target difficulty filter (EASY, MEDIUM, HARD).",
    )
    competency_id: Optional[int] = Field(
        default=None,
        description="Optional competency ID to focus topic retrieval and prompt constraints.",
    )


class QuestionResponse(BaseModel):
    """Public representation of an MCQ entity."""

    id: int
    document_id: Optional[int]
    competency_id: Optional[int]
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_option: str
    difficulty: QuestionDifficulty
    explanation: Optional[str] = None
    source_page: Optional[int] = None
    source_chunk_id: Optional[int] = None
    generation_model: Optional[str] = None
    status: QuestionStatus
    created_by: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QuestionListResponse(BaseModel):
    """Paginated response for questions query."""

    total: int
    items: List[QuestionResponse]


class QuestionReviewRequest(BaseModel):
    """Request payload for SME question review decision."""

    action: ReviewAction = Field(
        ...,
        description="Review decision action: APPROVE or REJECT.",
    )
    comment: Optional[str] = Field(
        default=None,
        description="Audit commentary, validation notes, or rejection rationale.",
    )


class QuestionReviewResponse(BaseModel):
    """Response returned upon reviewing a question, exposing the audit record and updated question."""

    id: int
    question_id: int
    reviewer_id: int
    action: ReviewAction
    comment: Optional[str] = None
    created_at: datetime
    question_status: QuestionStatus
    question: QuestionResponse

    model_config = ConfigDict(from_attributes=True)
