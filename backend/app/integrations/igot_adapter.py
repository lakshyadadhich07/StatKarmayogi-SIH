from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class BaseIGOTAdapter(ABC):
    """Abstract interface for iGOT Karmayogi integration.
    
    The iGOT adapter is an integration boundary, not a mandatory dependency
    in the core deterministic scoring algorithm. It abstracts external course
    discovery and metadata lookup to support clean future production integration.
    """

    @abstractmethod
    def get_courses(
        self,
        query: Optional[str] = None,
        competency_code: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Retrieve courses matching optional search query or competency code filter."""
        pass

    @abstractmethod
    def get_course_by_id(self, igot_course_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve details of a course by its iGOT identifier."""
        pass


class MockIGOTAdapter(BaseIGOTAdapter):
    """Local prototype implementation of the iGOT adapter.
    
    Operates strictly locally with zero external network requests and zero
    fictional external domains. Provides discovery access to reference iGOT-aligned
    prototype courses.
    """

    def __init__(self) -> None:
        self.catalogue_version = settings.MOCK_IGOT_CATALOGUE_VERSION
        # Reference in-memory mock catalog for prototype discovery boundaries
        self._mock_courses: List[Dict[str, Any]] = [
            {
                "igot_course_id": "IGOT-PROTO-ASI-01",
                "title": "Annual Survey of Industries (ASI): Frame, Concepts & Sampling",
                "description": "Comprehensive module on ASI methodology, industrial classification, frame preparation, and sampling design for MoSPI field officers.",
                "provider": "MoSPI Training Division / NSSTA",
                "language": "English",
                "difficulty": "Intermediate",
                "duration_minutes": 180,
                "course_url": None,
                "is_public": True,
                "source": "iGOT-Aligned Prototype",
                "competency_keywords": ["ASI", "Industrial Estimation", "Survey Methodology"],
            },
            {
                "igot_course_id": "IGOT-PROTO-IIP-01",
                "title": "Compilation of Index of Industrial Production (IIP) & Laspeyres Weighting",
                "description": "Practical guide to index numbers, item basket selection, base year revisions, and Laspeyres formula compilation in industrial statistics.",
                "provider": "Economic Statistics Division (ESD), MoSPI",
                "language": "English",
                "difficulty": "Beginner",
                "duration_minutes": 120,
                "course_url": None,
                "is_public": True,
                "source": "iGOT-Aligned Prototype",
                "competency_keywords": ["IIP", "Index of Industrial Production", "Laspeyres"],
            },
            {
                "igot_course_id": "IGOT-PROTO-NAS-01",
                "title": "National Accounts Statistics: Gross Value Added (GVA) & Fixed Capital",
                "description": "Advanced training on National Accounts aggregates, Gross Value Added (GVA), consumption of fixed capital, and SNA guidelines.",
                "provider": "National Accounts Division (NAD), MoSPI",
                "language": "English",
                "difficulty": "Hard",
                "duration_minutes": 240,
                "course_url": None,
                "is_public": True,
                "source": "iGOT-Aligned Prototype",
                "competency_keywords": ["National Accounts", "GVA", "NAD"],
            },
            {
                "igot_course_id": "IGOT-PROTO-SSD-01",
                "title": "Sample Survey Design & Multi-Stage Sampling in Official Statistics",
                "description": "Foundational course on sample design, stratified multi-stage sampling, sampling weights, and estimation errors in large-scale socio-economic surveys.",
                "provider": "Survey Design and Research Division (SDRD), MoSPI",
                "language": "English",
                "difficulty": "Intermediate",
                "duration_minutes": 150,
                "course_url": None,
                "is_public": True,
                "source": "iGOT-Aligned Prototype",
                "competency_keywords": ["Sample Survey Design", "Sampling", "SDRD"],
            },
            {
                "igot_course_id": "IGOT-PROTO-FPOS-01",
                "title": "Fundamental Principles of Official Statistics & Data Ethics",
                "description": "Overview of UN Fundamental Principles of Official Statistics, confidentiality, objectivity, data governance, and professional standards.",
                "provider": "National Statistical Systems Training Academy (NSSTA)",
                "language": "English",
                "difficulty": "Beginner",
                "duration_minutes": 90,
                "course_url": None,
                "is_public": True,
                "source": "iGOT-Aligned Prototype",
                "competency_keywords": ["Ethics", "Official Statistics", "Data Governance"],
            },
            {
                "igot_course_id": "IGOT-PROTO-DAP-01",
                "title": "Data Analytics & Statistical Analysis for Field Officers",
                "description": "Hands-on data analytics methodologies, descriptive statistics, outlier detection, and reporting techniques for statistical field personnel.",
                "provider": "Computer Centre, MoSPI",
                "language": "English",
                "difficulty": "Intermediate",
                "duration_minutes": 210,
                "course_url": None,
                "is_public": True,
                "source": "iGOT-Aligned Prototype",
                "competency_keywords": ["Data Analytics", "Field Statistics", "Analysis"],
            },
        ]

    def get_courses(
        self,
        query: Optional[str] = None,
        competency_code: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Filter local mock courses by query keyword or competency."""
        results = self._mock_courses

        if query:
            q = query.lower()
            results = [
                c for c in results
                if q in c["title"].lower() or q in c["description"].lower()
            ]

        if competency_code:
            code_lower = competency_code.lower()
            results = [
                c for c in results
                if any(code_lower in kw.lower() for kw in c.get("competency_keywords", []))
            ]

        return results[skip : skip + limit]

    def get_course_by_id(self, igot_course_id: str) -> Optional[Dict[str, Any]]:
        """Lookup mock course by iGOT identifier."""
        for c in self._mock_courses:
            if c["igot_course_id"] == igot_course_id:
                return c
        return None
