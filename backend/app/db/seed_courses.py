from decimal import Decimal
import logging
from typing import List, Optional
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.competency import Competency
from app.models.course import Course
from app.models.course_competency import CourseCompetency

logger = logging.getLogger(__name__)

PROTOTYPE_COURSES = [
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
        "is_active": True,
        "source": "iGOT-Aligned Prototype",
        "competency_code": "ASI_METH_73F0",
        "competency_name": "ASI Survey Methodology & Classification",
        "relevance_score": Decimal("0.95"),
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
        "is_active": True,
        "source": "iGOT-Aligned Prototype",
        "competency_code": "IIP_IND_94799B",
        "competency_name": "Index of Industrial Production (IIP)",
        "relevance_score": Decimal("0.90"),
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
        "is_active": True,
        "source": "iGOT-Aligned Prototype",
        "competency_code": "COMP_NAD_3746b0",
        "competency_name": "National Accounts & GVA",
        "relevance_score": Decimal("0.95"),
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
        "is_active": True,
        "source": "iGOT-Aligned Prototype",
        "competency_code": "COMP_D981F6",
        "competency_name": "Sample Survey Design",
        "relevance_score": Decimal("0.90"),
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
        "is_active": True,
        "source": "iGOT-Aligned Prototype",
        "competency_code": None,
        "competency_name": None,
        "relevance_score": None,
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
        "is_active": True,
        "source": "iGOT-Aligned Prototype",
        "competency_code": None,
        "competency_name": None,
        "relevance_score": None,
    },
]


def seed_courses(db: Optional[Session] = None) -> List[Course]:
    """Seed iGOT-aligned prototype courses and link them to verified active competencies.
    
    Protocol:
    - Only explicitly verified course-to-competency mappings are seeded. Courses for which the
      existing competency catalogue has no appropriate match remain unmapped and require future
      SME/MoSPI competency alignment.
    - No automatic fallback competency assignment is permitted.
    - Pre-verifies existing competencies in the database; no fake IDs or sequential assumptions.
    - Idempotently creates Course entities if not already existing.
    - Idempotently creates CourseCompetency records with curated prototype relevance scores for
      verified mappings only.
    - Cleans up any unverified/stale CourseCompetency records for unmapped courses.
    """
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    created_courses: List[Course] = []
    try:
        for course_def in PROTOTYPE_COURSES:
            existing_course = (
                db.query(Course)
                .filter(Course.igot_course_id == course_def["igot_course_id"])
                .first()
            )
            if not existing_course:
                course = Course(
                    igot_course_id=course_def["igot_course_id"],
                    title=course_def["title"],
                    description=course_def["description"],
                    provider=course_def["provider"],
                    language=course_def["language"],
                    difficulty=course_def["difficulty"],
                    duration_minutes=course_def["duration_minutes"],
                    course_url=course_def["course_url"],
                    is_public=course_def["is_public"],
                    is_active=course_def["is_active"],
                    source=course_def["source"],
                )
                db.add(course)
                db.flush()
                created_courses.append(course)
                logger.info(f"Created prototype course: {course.title} (ID={course.id})")
            else:
                course = existing_course
                logger.info(f"Course already exists: {course.title} (ID={course.id})")

            # Check if this course has an explicit verified competency mapping
            comp_code = course_def.get("competency_code")
            comp_name = course_def.get("competency_name")
            rel_score = course_def.get("relevance_score")

            if comp_code is None:
                # Course has no verified competency in existing catalogue
                # Clean up any stale/unverified mappings if present in the database
                stale_mappings = (
                    db.query(CourseCompetency)
                    .filter(CourseCompetency.course_id == course.id)
                    .all()
                )
                if stale_mappings:
                    for sm in stale_mappings:
                        db.delete(sm)
                    logger.info(
                        f"Cleaned up {len(stale_mappings)} unverified CourseCompetency mappings for '{course.title}'."
                    )
                logger.info(
                    f"Course '{course.title}' has no verified competency mapping in catalogue. "
                    "Leaving unmapped pending future SME/MoSPI competency alignment. "
                    "No automatic fallback competency assignment is permitted."
                )
                continue

            # Explicit verified mapping exists: resolve against database
            matched_comp = (
                db.query(Competency)
                .filter(Competency.code == comp_code, Competency.is_active == True)
                .first()
            )
            if not matched_comp and comp_name:
                matched_comp = (
                    db.query(Competency)
                    .filter(Competency.name == comp_name, Competency.is_active == True)
                    .first()
                )

            if matched_comp:
                existing_link = (
                    db.query(CourseCompetency)
                    .filter(
                        CourseCompetency.course_id == course.id,
                        CourseCompetency.competency_id == matched_comp.id,
                    )
                    .first()
                )
                if not existing_link:
                    link = CourseCompetency(
                        course_id=course.id,
                        competency_id=matched_comp.id,
                        relevance_score=rel_score,
                    )
                    db.add(link)
                    logger.info(
                        f"Linked course '{course.title}' to verified competency '{matched_comp.name}' "
                        f"(code={matched_comp.code}, score={rel_score})"
                    )
            else:
                logger.warning(
                    f"Verified competency '{comp_code}' not found in database for course '{course.title}'. "
                    "Course remains unmapped."
                )

        db.commit()
        return created_courses
    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding prototype courses: {e}", exc_info=True)
        raise
    finally:
        if should_close:
            db.close()


if __name__ == "__main__":
    logger.info("Starting course seeding...")
    res = seed_courses()
    logger.info(f"Course seeding complete. Added {len(res)} courses.")
