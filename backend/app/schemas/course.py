from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class CourseCompetencyResponse(BaseModel):
    """Competency mapping item for a course."""
    competency_id: int
    competency_code: Optional[str] = None
    competency_name: Optional[str] = None
    relevance_score: float

    model_config = ConfigDict(from_attributes=True)


class CourseResponse(BaseModel):
    """Core course attributes for catalogue listings."""
    id: int
    igot_course_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    provider: Optional[str] = None
    language: Optional[str] = "English"
    difficulty: Optional[str] = None
    duration_minutes: Optional[int] = None
    course_url: Optional[str] = None
    is_public: bool = True
    source: Optional[str] = "iGOT Karmayogi"
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CourseDetailResponse(CourseResponse):
    """Extended course detail including associated competency mappings."""
    competencies: List[CourseCompetencyResponse] = []

    model_config = ConfigDict(from_attributes=True)


class CourseListResponse(BaseModel):
    """Paginated course listing response."""
    total: int
    items: List[CourseResponse]

    model_config = ConfigDict(from_attributes=True)
