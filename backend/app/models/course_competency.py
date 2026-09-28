from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.course import Course
    from app.models.competency import Competency


class CourseCompetency(Base):
    """Mapping entity linking courses to competencies with relevance scores."""

    __tablename__ = "course_competencies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    competency_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("competencies.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    relevance_score: Mapped[Decimal] = mapped_column(
        Numeric(3, 2),
        default=Decimal("1.00"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("course_id", "competency_id", name="uq_course_competency"),
    )

    # Relationships
    course: Mapped["Course"] = relationship("Course", back_populates="course_competencies")
    competency: Mapped["Competency"] = relationship("Competency", back_populates="course_competencies")

    def __repr__(self) -> str:
        return f"<CourseCompetency(course_id={self.course_id}, competency_id={self.competency_id}, score={self.relevance_score})>"
