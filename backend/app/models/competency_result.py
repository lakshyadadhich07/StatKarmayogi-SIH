from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ProficiencyLevel

if TYPE_CHECKING:
    from app.models.assessment import Assessment
    from app.models.competency import Competency


class CompetencyResult(Base):
    """Competency-level assessment proficiency result entity."""

    __tablename__ = "competency_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assessment_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    competency_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("competencies.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    questions_attempted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    questions_correct: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    score_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    proficiency_level: Mapped[ProficiencyLevel] = mapped_column(
        SAEnum(ProficiencyLevel, name="proficiency_level_enum"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("assessment_id", "competency_id", name="uq_assessment_competency_result"),
    )

    # Relationships
    assessment: Mapped["Assessment"] = relationship("Assessment", back_populates="competency_results")
    competency: Mapped["Competency"] = relationship("Competency", back_populates="competency_results")

    def __repr__(self) -> str:
        return f"<CompetencyResult(assessment_id={self.assessment_id}, competency_id={self.competency_id}, level='{self.proficiency_level}')>"
