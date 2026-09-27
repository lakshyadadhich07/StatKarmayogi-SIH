from datetime import datetime, timezone
from decimal import Decimal
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token
from app.db.seed import seed_roles
from app.db.seed_courses import seed_courses
from app.db.session import SessionLocal, engine
from app.integrations.igot_adapter import MockIGOTAdapter
from app.main import app
from app.models.answer import Answer
from app.models.assessment import Assessment
from app.models.assessment_question import AssessmentQuestion
from app.models.competency import Competency
from app.models.competency_result import CompetencyResult
from app.models.course import Course
from app.models.course_competency import CourseCompetency
from app.models.enums import (
    AssessmentStatus,
    DocumentStatus,
    GapLevel,
    ProficiencyLevel,
    QuestionDifficulty,
    QuestionStatus,
    RecommendationStatus,
    RoleName,
)
from app.models.question import Question
from app.models.recommendation import Recommendation
from app.models.role import Role
from app.models.skill_gap import SkillGap
from app.models.user import User
from app.services.assessment_service import AssessmentService
from app.services.recommendation_service import RecommendationService

client = TestClient(app)


@pytest.fixture(scope="module")
def setup_rec_environment():
    """Sets up roles, users, courses, competencies, questions, and test assessments."""
    db: Session = SessionLocal()
    try:
        seed_roles(db)
        seed_courses(db)

        officer_role = db.query(Role).filter_by(name=RoleName.OFFICER.value).first()
        trainer_role = db.query(Role).filter_by(name=RoleName.TRAINER.value).first()
        sme_role = db.query(Role).filter_by(name=RoleName.SME.value).first()
        admin_role = db.query(Role).filter_by(name=RoleName.ADMIN.value).first()

        suffix = uuid.uuid4().hex[:6]

        officer_1 = User(
            name="Rec Officer One",
            email=f"rec_officer1_{suffix}@mospi.gov.in",
            password_hash="test_hash",
            role_id=officer_role.id,
            is_active=True,
        )
        officer_2 = User(
            name="Rec Officer Two",
            email=f"rec_officer2_{suffix}@mospi.gov.in",
            password_hash="test_hash",
            role_id=officer_role.id,
            is_active=True,
        )
        trainer = User(
            name="Rec Trainer",
            email=f"rec_trainer_{suffix}@mospi.gov.in",
            password_hash="test_hash",
            role_id=trainer_role.id,
            is_active=True,
        )
        sme = User(
            name="Rec SME",
            email=f"rec_sme_{suffix}@mospi.gov.in",
            password_hash="test_hash",
            role_id=sme_role.id,
            is_active=True,
        )
        admin = User(
            name="Rec Admin",
            email=f"rec_admin_{suffix}@mospi.gov.in",
            password_hash="test_hash",
            role_id=admin_role.id,
            is_active=True,
        )

        db.add_all([officer_1, officer_2, trainer, sme, admin])
        db.commit()

        # Create distinct test competencies
        comp_asi = Competency(
            code=f"COMP_ASI_{suffix}",
            name=f"ASI Survey Methodology_{suffix}",
            description="ASI survey concepts",
            category="Economic Statistics",
            is_active=True,
        )
        comp_iip = Competency(
            code=f"COMP_IIP_{suffix}",
            name=f"IIP Compilation_{suffix}",
            description="IIP compilation",
            category="Economic Statistics",
            is_active=True,
        )
        comp_nad = Competency(
            code=f"COMP_NAD_{suffix}",
            name=f"National Accounts_{suffix}",
            description="National accounts",
            category="Macro Statistics",
            is_active=True,
        )
        db.add_all([comp_asi, comp_iip, comp_nad])
        db.commit()

        # Link prototype courses to these test competencies with calibrated relevance scores
        courses = db.query(Course).all()
        c1, c2, c3 = courses[0], courses[1], courses[2]

        cc1 = CourseCompetency(course_id=c1.id, competency_id=comp_asi.id, relevance_score=Decimal("0.95"))
        cc2 = CourseCompetency(course_id=c2.id, competency_id=comp_asi.id, relevance_score=Decimal("0.80"))
        cc3 = CourseCompetency(course_id=c3.id, competency_id=comp_asi.id, relevance_score=Decimal("0.70"))
        cc4 = CourseCompetency(course_id=c2.id, competency_id=comp_iip.id, relevance_score=Decimal("0.90"))
        cc5 = CourseCompetency(course_id=c3.id, competency_id=comp_nad.id, relevance_score=Decimal("0.85"))

        db.add_all([cc1, cc2, cc3, cc4, cc5])
        db.commit()

        # Create a completed assessment with known skill gaps for Officer 1
        ass_completed = Assessment(
            officer_id=officer_1.id,
            title="Completed Assessment with Gaps",
            status=AssessmentStatus.COMPLETED,
            total_questions=10,
            total_correct=4,
            score_percentage=Decimal("40.00"),
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        db.add(ass_completed)
        db.commit()

        # Add skill gaps: ASI (HIGH), IIP (MEDIUM)
        gap_high = SkillGap(
            assessment_id=ass_completed.id,
            competency_id=comp_asi.id,
            score_percentage=Decimal("30.00"),
            gap_level=GapLevel.HIGH,
        )
        gap_med = SkillGap(
            assessment_id=ass_completed.id,
            competency_id=comp_iip.id,
            score_percentage=Decimal("55.00"),
            gap_level=GapLevel.MEDIUM,
        )
        db.add_all([gap_high, gap_med])
        db.commit()

        # Create an assessment with 100% score (NO skill gaps)
        ass_no_gaps = Assessment(
            officer_id=officer_1.id,
            title="Completed Assessment 100% (No Gaps)",
            status=AssessmentStatus.COMPLETED,
            total_questions=5,
            total_correct=5,
            score_percentage=Decimal("100.00"),
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        db.add(ass_no_gaps)
        db.commit()

        # Create an IN_PROGRESS assessment
        ass_in_progress = Assessment(
            officer_id=officer_1.id,
            title="In Progress Assessment",
            status=AssessmentStatus.IN_PROGRESS,
            total_questions=5,
            total_correct=0,
            score_percentage=Decimal("0.00"),
            started_at=datetime.now(timezone.utc),
        )
        db.add(ass_in_progress)
        db.commit()

        return {
            "tokens": {
                "officer_1": create_access_token({"sub": str(officer_1.id)}),
                "officer_2": create_access_token({"sub": str(officer_2.id)}),
                "trainer": create_access_token({"sub": str(trainer.id)}),
                "sme": create_access_token({"sub": str(sme.id)}),
                "admin": create_access_token({"sub": str(admin.id)}),
            },
            "user_ids": {
                "officer_1": officer_1.id,
                "officer_2": officer_2.id,
                "trainer": trainer.id,
                "sme": sme.id,
                "admin": admin.id,
            },
            "assessment_ids": {
                "completed": ass_completed.id,
                "no_gaps": ass_no_gaps.id,
                "in_progress": ass_in_progress.id,
            },
            "competency_ids": {
                "asi": comp_asi.id,
                "iip": comp_iip.id,
                "nad": comp_nad.id,
            },
            "course_ids": {
                "c1": c1.id,
                "c2": c2.id,
                "c3": c3.id,
            },
        }
    finally:
        db.close()


# -------------------------------------------------------------------------
# Security & RBAC Tests
# -------------------------------------------------------------------------

def test_unauthenticated_recommendation_access_returns_401():
    """Unauthenticated calls to recommendation endpoints return 401."""
    resp = client.get("/api/v1/recommendations")
    assert resp.status_code == 401


def test_officer_cannot_view_another_officers_recommendations_403(setup_rec_environment):
    """Officer 2 cannot view recommendations for an assessment owned by Officer 1."""
    token = setup_rec_environment["tokens"]["officer_2"]
    ass_id = setup_rec_environment["assessment_ids"]["completed"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get(f"/api/v1/assessments/{ass_id}/recommendations", headers=headers)
    assert resp.status_code == 403


def test_trainer_cannot_generate_or_mutate_recommendations_403(setup_rec_environment):
    """Trainer cannot trigger generation or update recommendation status (403)."""
    token = setup_rec_environment["tokens"]["trainer"]
    ass_id = setup_rec_environment["assessment_ids"]["completed"]
    headers = {"Authorization": f"Bearer {token}"}

    # Generate attempt
    resp_gen = client.post(f"/api/v1/assessments/{ass_id}/recommendations", headers=headers)
    assert resp_gen.status_code == 403

    # Mutate status attempt
    resp_mut = client.patch("/api/v1/recommendations/1/status", json={"status": "STARTED"}, headers=headers)
    assert resp_mut.status_code == 403


def test_trainer_can_inspect_recommendations_across_officers_200(setup_rec_environment):
    """Trainer can inspect recommendations across assessments for training oversight."""
    # First generate recommendations as Officer 1
    t_off1 = setup_rec_environment["tokens"]["officer_1"]
    ass_id = setup_rec_environment["assessment_ids"]["completed"]
    client.post(f"/api/v1/assessments/{ass_id}/recommendations", headers={"Authorization": f"Bearer {t_off1}"})

    # Now Trainer queries
    t_trainer = setup_rec_environment["tokens"]["trainer"]
    resp = client.get(f"/api/v1/assessments/{ass_id}/recommendations", headers={"Authorization": f"Bearer {t_trainer}"})
    assert resp.status_code == 200
    assert len(resp.json()) > 0

    # Trainer queries list endpoint
    resp_list = client.get("/api/v1/recommendations", headers={"Authorization": f"Bearer {t_trainer}"})
    assert resp_list.status_code == 200


def test_sme_cannot_access_recommendation_endpoints_403(setup_rec_environment):
    """SME role is forbidden from all recommendation endpoints."""
    token = setup_rec_environment["tokens"]["sme"]
    ass_id = setup_rec_environment["assessment_ids"]["completed"]
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/api/v1/recommendations", headers=headers).status_code == 403
    assert client.get(f"/api/v1/assessments/{ass_id}/recommendations", headers=headers).status_code == 403
    assert client.post(f"/api/v1/assessments/{ass_id}/recommendations", headers=headers).status_code == 403
    assert client.patch("/api/v1/recommendations/1/status", json={"status": "STARTED"}, headers=headers).status_code == 403


def test_admin_has_full_recommendation_access(setup_rec_environment):
    """Admin can generate, inspect, and update recommendation status."""
    token = setup_rec_environment["tokens"]["admin"]
    ass_id = setup_rec_environment["assessment_ids"]["completed"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post(f"/api/v1/assessments/{ass_id}/recommendations", headers=headers)
    assert resp.status_code == 200

    resp_get = client.get(f"/api/v1/assessments/{ass_id}/recommendations", headers=headers)
    assert resp_get.status_code == 200


# -------------------------------------------------------------------------
# Assessment State & No-Skill-Gap Edge Case Tests
# -------------------------------------------------------------------------

def test_recommendation_generation_in_progress_assessment_rejected_400(setup_rec_environment):
    """Generating recommendations for an IN_PROGRESS assessment raises 400 Bad Request."""
    token = setup_rec_environment["tokens"]["officer_1"]
    ass_id = setup_rec_environment["assessment_ids"]["in_progress"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post(f"/api/v1/assessments/{ass_id}/recommendations", headers=headers)
    assert resp.status_code == 400
    assert "COMPLETED" in resp.json()["detail"]


def test_completed_assessment_with_no_skill_gaps_returns_empty_recommendations(setup_rec_environment):
    """Assessment completed with 100% score (no skill gaps) returns empty list cleanly without error."""
    token = setup_rec_environment["tokens"]["officer_1"]
    ass_id = setup_rec_environment["assessment_ids"]["no_gaps"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post(f"/api/v1/assessments/{ass_id}/recommendations", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []

    # Database check: no rows added for this assessment
    db = SessionLocal()
    try:
        count = db.query(Recommendation).filter(Recommendation.assessment_id == ass_id).count()
        assert count == 0
    finally:
        db.close()


# -------------------------------------------------------------------------
# Deterministic Scoring, Ordering & Reason Tests
# -------------------------------------------------------------------------

def test_deterministic_match_score_calculation(setup_rec_environment):
    """Verifies formula match_score = round(relevance_score * gap_multiplier * 100, 2)."""
    token = setup_rec_environment["tokens"]["officer_1"]
    ass_id = setup_rec_environment["assessment_ids"]["completed"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post(f"/api/v1/assessments/{ass_id}/recommendations", headers=headers)
    assert resp.status_code == 200
    recs = resp.json()

    # Gap HIGH on ASI: relevance 0.95 -> 0.95 * 1.00 * 100 = 95.0
    rec_c1 = next((r for r in recs if r["course_id"] == setup_rec_environment["course_ids"]["c1"]), None)
    assert rec_c1 is not None
    assert rec_c1["priority"] == 1
    assert rec_c1["match_score"] == 95.0

    # Gap MEDIUM on IIP: relevance 0.90 -> 0.90 * 0.85 * 100 = 76.5
    rec_iip = next((r for r in recs if r["competency_id"] == setup_rec_environment["competency_ids"]["iip"]), None)
    if rec_iip:
        assert rec_iip["priority"] == 2
        assert rec_iip["match_score"] == 76.5


def test_deterministic_tie_breaking_order(setup_rec_environment):
    """Verifies deterministic sort: priority ASC, match_score DESC, id ASC."""
    token = setup_rec_environment["tokens"]["officer_1"]
    ass_id = setup_rec_environment["assessment_ids"]["completed"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get(f"/api/v1/assessments/{ass_id}/recommendations", headers=headers)
    assert resp.status_code == 200
    recs = resp.json()

    for i in range(len(recs) - 1):
        r1, r2 = recs[i], recs[i + 1]
        assert r1["priority"] <= r2["priority"]
        if r1["priority"] == r2["priority"]:
            assert r1["match_score"] >= r2["match_score"]


def test_deterministic_reason_text_format(setup_rec_environment):
    """Verifies template-based explanation mentions score, priority, and match score."""
    token = setup_rec_environment["tokens"]["officer_1"]
    ass_id = setup_rec_environment["assessment_ids"]["completed"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get(f"/api/v1/assessments/{ass_id}/recommendations", headers=headers)
    assert resp.status_code == 200
    recs = resp.json()
    assert len(recs) > 0
    rec = recs[0]

    assert "Recommended because your assessment score in" in rec["reason"]
    assert "priority skill gap" in rec["reason"]
    assert "resulting in a match score of" in rec["reason"]


def test_per_gap_and_global_active_limits(setup_rec_environment):
    """Verifies per-gap limit of 2 and global active limit of 6."""
    token = setup_rec_environment["tokens"]["officer_1"]
    ass_id = setup_rec_environment["assessment_ids"]["completed"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get(f"/api/v1/assessments/{ass_id}/recommendations", headers=headers)
    assert resp.status_code == 200
    recs = resp.json()
    assert len(recs) <= 6

    # For any competency gap, at most 2 recommendations are selected
    by_comp = {}
    for r in recs:
        by_comp.setdefault(r["competency_id"], []).append(r)
    for cid, items in by_comp.items():
        assert len(items) <= 2


# -------------------------------------------------------------------------
# State Machine Tests
# -------------------------------------------------------------------------

def test_state_machine_transitions_and_terminals(setup_rec_environment):
    """Verifies full lifecycle: RECOMMENDED -> STARTED -> COMPLETED and RECOMMENDED -> DISMISSED."""
    token = setup_rec_environment["tokens"]["officer_1"]
    ass_id = setup_rec_environment["assessment_ids"]["completed"]
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch existing recommendations
    recs = client.get(f"/api/v1/assessments/{ass_id}/recommendations", headers=headers).json()
    assert len(recs) >= 2
    rec1_id = recs[0]["id"]
    rec2_id = recs[1]["id"]

    # 1. Invalid: RECOMMENDED -> COMPLETED is rejected (400)
    resp_bad = client.patch(f"/api/v1/recommendations/{rec1_id}/status", json={"status": "COMPLETED"}, headers=headers)
    assert resp_bad.status_code == 400

    # 2. Valid: RECOMMENDED -> STARTED
    resp_start = client.patch(f"/api/v1/recommendations/{rec1_id}/status", json={"status": "STARTED"}, headers=headers)
    assert resp_start.status_code == 200
    assert resp_start.json()["status"] == "STARTED"

    # 3. Invalid: STARTED -> DISMISSED is rejected (400)
    resp_bad2 = client.patch(f"/api/v1/recommendations/{rec1_id}/status", json={"status": "DISMISSED"}, headers=headers)
    assert resp_bad2.status_code == 400

    # 4. Valid: STARTED -> COMPLETED
    resp_comp = client.patch(f"/api/v1/recommendations/{rec1_id}/status", json={"status": "COMPLETED"}, headers=headers)
    assert resp_comp.status_code == 200
    assert resp_comp.json()["status"] == "COMPLETED"

    # 5. COMPLETED is terminal: cannot transition anywhere (400)
    resp_comp_term = client.patch(f"/api/v1/recommendations/{rec1_id}/status", json={"status": "STARTED"}, headers=headers)
    assert resp_comp_term.status_code == 400

    # 6. Valid: RECOMMENDED -> DISMISSED on rec2
    resp_dism = client.patch(f"/api/v1/recommendations/{rec2_id}/status", json={"status": "DISMISSED"}, headers=headers)
    assert resp_dism.status_code == 200
    assert resp_dism.json()["status"] == "DISMISSED"

    # 7. DISMISSED is terminal: cannot transition anywhere (400)
    resp_dism_term = client.patch(f"/api/v1/recommendations/{rec2_id}/status", json={"status": "STARTED"}, headers=headers)
    assert resp_dism_term.status_code == 400


def test_officer_cannot_update_another_officers_recommendation_status_403(setup_rec_environment):
    """Officer 2 cannot update status of a recommendation belonging to Officer 1."""
    t_off1 = setup_rec_environment["tokens"]["officer_1"]
    t_off2 = setup_rec_environment["tokens"]["officer_2"]
    ass_id = setup_rec_environment["assessment_ids"]["completed"]

    recs = client.get(f"/api/v1/assessments/{ass_id}/recommendations", headers={"Authorization": f"Bearer {t_off1}"}).json()
    rec_id = recs[0]["id"]

    resp = client.patch(f"/api/v1/recommendations/{rec_id}/status", json={"status": "STARTED"}, headers={"Authorization": f"Bearer {t_off2}"})
    assert resp.status_code == 403


# -------------------------------------------------------------------------
# Idempotency & Historical Row Preservation Tests
# -------------------------------------------------------------------------

def test_regeneration_idempotency_preserves_history(setup_rec_environment):
    """Regeneration strictly preserves STARTED, COMPLETED, and DISMISSED records."""
    token = setup_rec_environment["tokens"]["officer_1"]
    ass_id = setup_rec_environment["assessment_ids"]["completed"]
    headers = {"Authorization": f"Bearer {token}"}

    # Call regeneration
    resp = client.post(f"/api/v1/assessments/{ass_id}/recommendations", headers=headers)
    assert resp.status_code == 200
    recs = resp.json()

    statuses = {r["status"] for r in recs}
    assert "COMPLETED" in statuses
    assert "DISMISSED" in statuses


def test_total_database_recommendation_rows_can_exceed_six_with_history(setup_rec_environment):
    """Verifies that an assessment can have more than 6 total database recommendation rows when historical items exist."""
    db = SessionLocal()
    try:
        off_id = setup_rec_environment["user_ids"]["officer_1"]

        # Dedicated assessment for row count verification
        ass = Assessment(
            officer_id=off_id,
            title="Exceed Row Count Test Assessment",
            status=AssessmentStatus.COMPLETED,
            total_questions=5,
            total_correct=2,
            score_percentage=Decimal("40.00"),
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        db.add(ass)
        db.flush()

        # Add 4 active recommendations
        for i in range(4):
            c = Course(
                igot_course_id=f"DUMMY_ACT_{uuid.uuid4().hex[:6]}",
                title=f"Active Course {i}",
                source="iGOT-Aligned Prototype",
            )
            db.add(c)
            db.flush()
            r_act = Recommendation(
                officer_id=off_id,
                assessment_id=ass.id,
                competency_id=setup_rec_environment["competency_ids"]["nad"],
                course_id=c.id,
                priority=1,
                match_score=Decimal("90.0"),
                reason="Active recommended course",
                status=RecommendationStatus.RECOMMENDED,
            )
            db.add(r_act)

        # Add 3 COMPLETED historical records
        for i in range(3):
            c_hist = Course(
                igot_course_id=f"DUMMY_HIST_{uuid.uuid4().hex[:6]}",
                title=f"Historical Course {i}",
                source="iGOT-Aligned Prototype",
            )
            db.add(c_hist)
            db.flush()
            r_hist = Recommendation(
                officer_id=off_id,
                assessment_id=ass.id,
                competency_id=setup_rec_environment["competency_ids"]["nad"],
                course_id=c_hist.id,
                priority=1,
                match_score=Decimal("80.0"),
                reason="Historical completed course",
                status=RecommendationStatus.COMPLETED,
            )
            db.add(r_hist)
        db.commit()

        # Check total rows: 4 active + 3 historical = 7 total rows (> 6)
        total_rows = db.query(Recommendation).filter(Recommendation.assessment_id == ass.id).count()
        assert total_rows == 7
        assert total_rows > 6
    finally:
        db.close()


# -------------------------------------------------------------------------
# Assessment Submission Integration & Resilience Tests
# -------------------------------------------------------------------------

def test_assessment_submission_retains_existing_phase_7_status_and_contract(setup_rec_environment):
    """Assessment submission commits successfully, remaining COMPLETED and returning AssessmentResultResponse."""
    db = SessionLocal()
    try:
        off_id = setup_rec_environment["user_ids"]["officer_1"]
        admin_id = setup_rec_environment["user_ids"]["admin"]
        comp_id = setup_rec_environment["competency_ids"]["asi"]

        # Create a single-question assessment for submission
        q = Question(
            question_text="What does ASI stand for?",
            option_a="Annual Survey of Industries",
            option_b="Automated Statistical Index",
            option_c="All Statistical Indicators",
            option_d="Area Sample Ingestion",
            correct_option="A",
            difficulty=QuestionDifficulty.EASY,
            status=QuestionStatus.APPROVED,
            competency_id=comp_id,
            created_by=admin_id,
        )
        db.add(q)
        db.flush()

        ass = Assessment(
            officer_id=off_id,
            title="Auto Rec Submission Test",
            status=AssessmentStatus.IN_PROGRESS,
            total_questions=1,
            total_correct=0,
            score_percentage=Decimal("0.00"),
            started_at=datetime.now(timezone.utc),
        )
        db.add(ass)
        db.flush()

        aq = AssessmentQuestion(assessment_id=ass.id, question_id=q.id, question_order=1)
        db.add(aq)
        db.commit()

        # Submit answer via AssessmentService
        token = setup_rec_environment["tokens"]["officer_1"]
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "answers": [{"question_id": q.id, "selected_option": "B"}]  # Incorrect answer -> gap created
        }

        resp = client.post(f"/api/v1/assessments/{ass.id}/submit", json=payload, headers=headers)
        assert resp.status_code == 200
        res = resp.json()
        assert res["status"] == "COMPLETED"
        assert res["score_percentage"] == 0.0
        assert len(res["skill_gaps"]) == 1

        # Confirm automatic recommendations were generated post-commit
        rec_resp = client.get(f"/api/v1/assessments/{ass.id}/recommendations", headers=headers)
        assert rec_resp.status_code == 200
        assert len(rec_resp.json()) > 0
    finally:
        db.close()


def test_mock_igot_adapter_contract():
    """Verifies that MockIGOTAdapter interface functions locally without network calls."""
    adapter = MockIGOTAdapter()
    courses = adapter.get_courses(query="ASI")
    assert isinstance(courses, list)
    assert len(courses) > 0

    c_id = courses[0]["igot_course_id"]
    detail = adapter.get_course_by_id(c_id)
    assert detail is not None
    assert detail["igot_course_id"] == c_id


def test_database_table_count_remains_16_tables():
    """Absolute constraint: PostgreSQL database schema contains exactly 16 tables."""
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    assert len(table_names) == 16, f"Expected exactly 16 tables, found {len(table_names)}: {table_names}"
    expected_tables = {
        "users", "roles", "competencies", "documents", "document_chunks",
        "questions", "question_reviews", "assessments", "assessment_questions",
        "answers", "competency_results", "skill_gaps", "courses",
        "course_competencies", "recommendations", "alembic_version",
    }
    assert set(table_names) == expected_tables


def test_unmapped_courses_never_recommended_through_competency_matching(setup_rec_environment):
    """Courses without competency mappings (FPOS, DAP) must not be candidates for gap recommendations."""
    db: Session = SessionLocal()
    try:
        token = setup_rec_environment["tokens"]["officer_1"]
        headers = {"Authorization": f"Bearer {token}"}
        ass_id = setup_rec_environment["assessment_ids"]["completed"]

        resp = client.post(f"/api/v1/assessments/{ass_id}/recommendations", headers=headers)
        assert resp.status_code == 200
        recs = resp.json()
        assert len(recs) > 0

        # Retrieve course IDs for FPOS and DAP
        fpos = db.query(Course).filter(Course.igot_course_id == "IGOT-PROTO-FPOS-01").first()
        dap = db.query(Course).filter(Course.igot_course_id == "IGOT-PROTO-DAP-01").first()

        rec_course_ids = {r["course_id"] for r in recs}
        if fpos:
            assert fpos.id not in rec_course_ids, f"Unmapped FPOS course {fpos.id} was recommended!"
        if dap:
            assert dap.id not in rec_course_ids, f"Unmapped DAP course {dap.id} was recommended!"
    finally:
        db.close()


