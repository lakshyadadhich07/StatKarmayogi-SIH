from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.assessment import Assessment
    from app.models.question import Question


class Answer(Base):
    """Officer response record with deterministic evaluation result."""

    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assessment_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("questions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    selected_option: Mapped[str] = mapped_column(String(1), nullable=False)  # A, B, C, or D
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    answered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("assessment_id", "question_id", name="uq_assessment_question_answer"),
    )

    # Relationships
    assessment: Mapped["Assessment"] = relationship("Assessment", back_populates="answers")
    question: Mapped["Question"] = relationship("Question", back_populates="answers")

    def __repr__(self) -> str:
        return f"<Answer(assessment_id={self.assessment_id}, question_id={self.question_id}, is_correct={self.is_correct})>"
