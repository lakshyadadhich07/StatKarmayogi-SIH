from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import QuestionDifficulty, QuestionStatus

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.competency import Competency
    from app.models.document_chunk import DocumentChunk
    from app.models.user import User
    from app.models.question_review import QuestionReview
    from app.models.assessment_question import AssessmentQuestion
    from app.models.answer import Answer


class Question(Base):
    """AI-generated MCQ entity linked to source grounding and review status."""

    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("documents.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    competency_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("competencies.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    option_a: Mapped[str] = mapped_column(Text, nullable=False)
    option_b: Mapped[str] = mapped_column(Text, nullable=False)
    option_c: Mapped[str] = mapped_column(Text, nullable=False)
    option_d: Mapped[str] = mapped_column(Text, nullable=False)
    correct_option: Mapped[str] = mapped_column(String(1), nullable=False)  # A, B, C, or D
    difficulty: Mapped[QuestionDifficulty] = mapped_column(
        SAEnum(QuestionDifficulty, name="question_difficulty_enum"),
        default=QuestionDifficulty.MEDIUM,
        nullable=False,
        index=True,
    )
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_chunk_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("document_chunks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    generation_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[QuestionStatus] = mapped_column(
        SAEnum(QuestionStatus, name="question_status_enum"),
        default=QuestionStatus.PENDING_REVIEW,
        nullable=False,
        index=True,
    )
    created_by: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    document: Mapped[Optional["Document"]] = relationship("Document", back_populates="questions")
    competency: Mapped[Optional["Competency"]] = relationship("Competency", back_populates="questions")
    source_chunk: Mapped[Optional["DocumentChunk"]] = relationship("DocumentChunk", back_populates="questions")
    creator: Mapped["User"] = relationship("User", back_populates="questions_created")
    reviews: Mapped[List["QuestionReview"]] = relationship(
        "QuestionReview",
        back_populates="question",
        cascade="all, delete-orphan",
    )
    assessment_questions: Mapped[List["AssessmentQuestion"]] = relationship(
        "AssessmentQuestion",
        back_populates="question",
        passive_deletes="all",
    )
    answers: Mapped[List["Answer"]] = relationship(
        "Answer",
        back_populates="question",
        passive_deletes="all",
    )

    def __repr__(self) -> str:
        return f"<Question(id={self.id}, difficulty='{self.difficulty}', status='{self.status}')>"
