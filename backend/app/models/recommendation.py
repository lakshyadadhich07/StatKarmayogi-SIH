from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, Numeric, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import RecommendationStatus

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.assessment import Assessment
    from app.models.competency import Competency
    from app.models.course import Course


class Recommendation(Base):
    """Explainable course recommendation entity for an officer assessment."""

    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    officer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
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
    course_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("courses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    match_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[RecommendationStatus] = mapped_column(
        SAEnum(RecommendationStatus, name="recommendation_status_enum"),
        default=RecommendationStatus.RECOMMENDED,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    officer: Mapped["User"] = relationship("User", back_populates="recommendations")
    assessment: Mapped["Assessment"] = relationship("Assessment", back_populates="recommendations")
    competency: Mapped["Competency"] = relationship("Competency", back_populates="recommendations")
    course: Mapped["Course"] = relationship("Course", back_populates="recommendations")

    def __repr__(self) -> str:
        return f"<Recommendation(id={self.id}, officer_id={self.officer_id}, course_id={self.course_id}, score={self.match_score})>"
