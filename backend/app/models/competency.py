from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.question import Question
    from app.models.competency_result import CompetencyResult
    from app.models.skill_gap import SkillGap
    from app.models.course_competency import CourseCompetency
    from app.models.recommendation import Recommendation


class Competency(Base):
    """Competency/topic taxonomy entity (derived dynamically from MoSPI manuals)."""

    __tablename__ = "competencies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    # Relationships
    questions: Mapped[List["Question"]] = relationship("Question", back_populates="competency")
    competency_results: Mapped[List["CompetencyResult"]] = relationship(
        "CompetencyResult",
        back_populates="competency",
    )
    skill_gaps: Mapped[List["SkillGap"]] = relationship("SkillGap", back_populates="competency")
    course_competencies: Mapped[List["CourseCompetency"]] = relationship(
        "CourseCompetency",
        back_populates="competency",
    )
    recommendations: Mapped[List["Recommendation"]] = relationship(
        "Recommendation",
        back_populates="competency",
    )

    def __repr__(self) -> str:
        return f"<Competency(id={self.id}, code='{self.code}', name='{self.name}')>"
