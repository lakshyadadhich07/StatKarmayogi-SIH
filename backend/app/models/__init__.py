"""SQLAlchemy models package exposing all 15 core entities and domain enums."""
from app.models.answer import Answer
from app.models.assessment import Assessment
from app.models.assessment_question import AssessmentQuestion
from app.models.competency import Competency
from app.models.competency_result import CompetencyResult
from app.models.course import Course
from app.models.course_competency import CourseCompetency
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.enums import (
    AssessmentStatus,
    DocumentStatus,
    GapLevel,
    ProficiencyLevel,
    QuestionDifficulty,
    QuestionStatus,
    RecommendationStatus,
    ReviewAction,
    RoleName,
)
from app.models.question import Question
from app.models.question_review import QuestionReview
from app.models.recommendation import Recommendation
from app.models.role import Role
from app.models.skill_gap import SkillGap
from app.models.user import User

__all__ = [
    # 15 Entities
    "Role",
    "User",
    "Competency",
    "Document",
    "DocumentChunk",
    "Question",
    "QuestionReview",
    "Assessment",
    "AssessmentQuestion",
    "Answer",
    "CompetencyResult",
    "SkillGap",
    "Course",
    "CourseCompetency",
    "Recommendation",
    # Enums
    "RoleName",
    "DocumentStatus",
    "QuestionDifficulty",
    "QuestionStatus",
    "ReviewAction",
    "AssessmentStatus",
    "ProficiencyLevel",
    "GapLevel",
    "RecommendationStatus",
]
