import enum


class RoleName(str, enum.Enum):
    """Supported system roles."""
    TRAINER = "TRAINER"
    SME = "SME"
    OFFICER = "OFFICER"
    ADMIN = "ADMIN"


class DocumentStatus(str, enum.Enum):
    """Document processing workflow status."""
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"


class QuestionDifficulty(str, enum.Enum):
    """MCQ difficulty classification."""
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class QuestionStatus(str, enum.Enum):
    """MCQ SME review status."""
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ReviewAction(str, enum.Enum):
    """SME audit review action."""
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class AssessmentStatus(str, enum.Enum):
    """Officer assessment state."""
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class ProficiencyLevel(str, enum.Enum):
    """Deterministic competency proficiency level."""
    BEGINNER = "BEGINNER"
    DEVELOPING = "DEVELOPING"
    PROFICIENT = "PROFICIENT"
    ADVANCED = "ADVANCED"


class GapLevel(str, enum.Enum):
    """Severity of identified skill gap."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RecommendationStatus(str, enum.Enum):
    """Status of course recommendation for an officer."""
    RECOMMENDED = "RECOMMENDED"
    STARTED = "STARTED"
    COMPLETED = "COMPLETED"
    DISMISSED = "DISMISSED"
