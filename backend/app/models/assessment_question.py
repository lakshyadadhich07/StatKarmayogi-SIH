from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.assessment import Assessment
    from app.models.question import Question


class AssessmentQuestion(Base):
    """Mapping table linking questions to an assessment with ordering."""

    __tablename__ = "assessment_questions"

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
    question_order: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("assessment_id", "question_id", name="uq_assessment_question"),
        UniqueConstraint("assessment_id", "question_order", name="uq_assessment_question_order"),
    )

    # Relationships
    assessment: Mapped["Assessment"] = relationship("Assessment", back_populates="assessment_questions")
    question: Mapped["Question"] = relationship("Question", back_populates="assessment_questions")

    def __repr__(self) -> str:
        return f"<AssessmentQuestion(assessment_id={self.assessment_id}, question_id={self.question_id}, order={self.question_order})>"
