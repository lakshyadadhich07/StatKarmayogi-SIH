from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.role import Role
    from app.models.document import Document
    from app.models.question import Question
    from app.models.question_review import QuestionReview
    from app.models.assessment import Assessment
    from app.models.recommendation import Recommendation


class User(Base):
    """User account entity storing identity and registration role."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("roles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    department: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    designation: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
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
    role: Mapped["Role"] = relationship("Role", back_populates="users")
    documents: Mapped[List["Document"]] = relationship("Document", back_populates="uploader")
    questions_created: Mapped[List["Question"]] = relationship("Question", back_populates="creator")
    reviews: Mapped[List["QuestionReview"]] = relationship("QuestionReview", back_populates="reviewer")
    assessments: Mapped[List["Assessment"]] = relationship("Assessment", back_populates="officer")
    recommendations: Mapped[List["Recommendation"]] = relationship("Recommendation", back_populates="officer")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', role_id={self.role_id})>"
