from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import RecommendationStatus


class RecommendationStatusUpdateRequest(BaseModel):
    """Payload to update recommendation status along the valid state machine."""
    status: RecommendationStatus = Field(
        ...,
        description="Target status (STARTED, COMPLETED, or DISMISSED)",
    )


class RecommendationResponse(BaseModel):
    """Explainable course recommendation item."""
    id: int
    officer_id: int
    assessment_id: int
    competency_id: int
    competency_code: Optional[str] = None
    competency_name: Optional[str] = None
    course_id: int
    course_title: str
    course_url: Optional[str] = None
    course_provider: Optional[str] = None
    course_duration_minutes: Optional[int] = None
    course_difficulty: Optional[str] = None
    priority: int = Field(..., description="1 = High, 2 = Medium, 3 = Low")
    match_score: float = Field(..., description="Calculated deterministic match percentage")
    reason: str = Field(..., description="Template-based explainable diagnostic reason")
    status: RecommendationStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecommendationListResponse(BaseModel):
    """Paginated list of recommendations."""
    total: int
    items: List[RecommendationResponse]


class LearningPathwayResponse(BaseModel):
    """Consolidated learning pathway for an assessment."""
    assessment_id: int
    officer_id: int
    total_recommendations: int
    high_priority_count: int
    recommendations: List[RecommendationResponse]

    model_config = ConfigDict(from_attributes=True)
