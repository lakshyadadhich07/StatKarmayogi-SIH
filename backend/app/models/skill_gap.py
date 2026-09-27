from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import GapLevel

if TYPE_CHECKING:
    from app.models.assessment import Assessment
    from app.models.competency import Competency


class SkillGap(Base):
    """Identified competency deficiency entity."""

    __tablename__ = "skill_gaps"

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
    score_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    gap_level: Mapped[GapLevel] = mapped_column(
        SAEnum(GapLevel, name="gap_level_enum"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("assessment_id", "competency_id", name="uq_assessment_competency_gap"),
    )

    # Relationships
    assessment: Mapped["Assessment"] = relationship("Assessment", back_populates="skill_gaps")
    competency: Mapped["Competency"] = relationship("Competency", back_populates="skill_gaps")

    def __repr__(self) -> str:
        return f"<SkillGap(assessment_id={self.assessment_id}, competency_id={self.competency_id}, gap='{self.gap_level}')>"
