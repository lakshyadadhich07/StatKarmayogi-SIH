from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import AssessmentStatus

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.assessment_question import AssessmentQuestion
    from app.models.answer import Answer
    from app.models.competency_result import CompetencyResult
    from app.models.skill_gap import SkillGap
    from app.models.recommendation import Recommendation


class Assessment(Base):
    """Officer assessment instance entity."""

    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    officer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[AssessmentStatus] = mapped_column(
        SAEnum(AssessmentStatus, name="assessment_status_enum"),
        default=AssessmentStatus.IN_PROGRESS,
        nullable=False,
        index=True,
    )
    total_questions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_correct: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    score_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    officer: Mapped["User"] = relationship("User", back_populates="assessments")
    assessment_questions: Mapped[List["AssessmentQuestion"]] = relationship(
        "AssessmentQuestion",
        back_populates="assessment",
        cascade="all, delete-orphan",
    )
    answers: Mapped[List["Answer"]] = relationship(
        "Answer",
        back_populates="assessment",
        cascade="all, delete-orphan",
    )
    competency_results: Mapped[List["CompetencyResult"]] = relationship(
        "CompetencyResult",
        back_populates="assessment",
        cascade="all, delete-orphan",
    )
    skill_gaps: Mapped[List["SkillGap"]] = relationship(
        "SkillGap",
        back_populates="assessment",
        cascade="all, delete-orphan",
    )
    recommendations: Mapped[List["Recommendation"]] = relationship(
        "Recommendation",
        back_populates="assessment",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Assessment(id={self.id}, officer_id={self.officer_id}, status='{self.status}', score={self.score_percentage})>"
