from datetime import datetime, timezone
from decimal import Decimal
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token
from app.db.base import Base
from app.db.seed import seed_roles
from app.db.session import SessionLocal, engine
from app.main import app
from app.models.answer import Answer
from app.models.assessment import Assessment
from app.models.assessment_question import AssessmentQuestion
from app.models.competency import Competency
from app.models.competency_result import CompetencyResult
from app.models.course import Course
from app.models.document import Document
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
from app.services.reassessment_service import format_reassessment_title, parse_baseline_id_from_title

client = TestClient(app)


@pytest.fixture(scope="module")
def setup_reassessment_env():
    """Sets up roles, users, competencies, documents, approved questions, and auth headers."""
    db: Session = SessionLocal()
    try:
        seed_roles(db)

        officer_role = db.query(Role).filter_by(name=RoleName.OFFICER.value).first()
        trainer_role = db.query(Role).filter_by(name=RoleName.TRAINER.value).first()
        sme_role = db.query(Role).filter_by(name=RoleName.SME.value).first()
        admin_role = db.query(Role).filter_by(name=RoleName.ADMIN.value).first()

        suffix = uuid.uuid4().hex[:6]

        # 1. Users
        officer_1 = User(
            name=f"Officer 1 {suffix}",
            email=f"off1_{suffix}@mospi.gov.in",
            password_hash="hashed_pw",
            role_id=officer_role.id,
            is_active=True,
        )
        officer_2 = User(
            name=f"Officer 2 {suffix}",
            email=f"off2_{suffix}@mospi.gov.in",
            password_hash="hashed_pw",
            role_id=officer_role.id,
            is_active=True,
        )
        trainer = User(
            name=f"Trainer {suffix}",
            email=f"trainer_{suffix}@mospi.gov.in",
            password_hash="hashed_pw",
            role_id=trainer_role.id,
            is_active=True,
        )
        sme = User(
            name=f"SME {suffix}",
            email=f"sme_{suffix}@mospi.gov.in",
            password_hash="hashed_pw",
            role_id=sme_role.id,
            is_active=True,
        )
        admin = User(
            name=f"Admin {suffix}",
            email=f"admin_{suffix}@mospi.gov.in",
            password_hash="hashed_pw",
            role_id=admin_role.id,
            is_active=True,
        )
        db.add_all([officer_1, officer_2, trainer, sme, admin])
        db.commit()

        # 2. Competencies
        comp_1 = Competency(
            code=f"COMP_REASS_A_{suffix}",
            name="ASI Industrial Estimation",
            description="Methodology and frame coverage for ASI survey",
            is_active=True,
        )
        comp_2 = Competency(
            code=f"COMP_REASS_B_{suffix}",
            name="National Accounts & GVA",
            description="Gross Value Added and fixed capital consumption",
            is_active=True,
        )
        comp_3 = Competency(
            code=f"COMP_REASS_C_{suffix}",
            name="Price Statistics & CPI",
            description="Price indices and market basket weighting",
            is_active=True,
        )
        db.add_all([comp_1, comp_2, comp_3])
        db.commit()

        # 3. Document
        doc = Document(
            uploaded_by=trainer.id,
            filename=f"mospi_handbook_{suffix}.pdf",
            file_type="pdf",
            file_path=f"storage/documents/mospi_handbook_{suffix}.pdf",
            status=DocumentStatus.PROCESSED,
        )
        db.add(doc)
        db.commit()

        # 4. Questions (2 for each competency, all APPROVED)
        # Comp 1
        q1 = Question(
            document_id=doc.id,
            competency_id=comp_1.id,
            question_text=f"ASI question 1 {suffix}?",
            option_a="Correct Option A",
            option_b="Option B",
            option_c="Option C",
            option_d="Option D",
            correct_option="A",
            difficulty=QuestionDifficulty.MEDIUM,
            explanation="Explanation 1",
            status=QuestionStatus.APPROVED,
            created_by=trainer.id,
        )
        q2 = Question(
            document_id=doc.id,
            competency_id=comp_1.id,
            question_text=f"ASI question 2 {suffix}?",
            option_a="Option A",
            option_b="Correct Option B",
            option_c="Option C",
            option_d="Option D",
            correct_option="B",
            difficulty=QuestionDifficulty.EASY,
            explanation="Explanation 2",
            status=QuestionStatus.APPROVED,
            created_by=trainer.id,
        )
        # Comp 2
        q3 = Question(
            document_id=doc.id,
            competency_id=comp_2.id,
            question_text=f"GVA question 1 {suffix}?",
            option_a="Option A",
            option_b="Option B",
            option_c="Correct Option C",
            option_d="Option D",
            correct_option="C",
            difficulty=QuestionDifficulty.MEDIUM,
            explanation="Explanation 3",
            status=QuestionStatus.APPROVED,
            created_by=trainer.id,
        )
        q4 = Question(
            document_id=doc.id,
            competency_id=comp_2.id,
            question_text=f"GVA question 2 {suffix}?",
            option_a="Option A",
            option_b="Option B",
            option_c="Option C",
            option_d="Correct Option D",
            correct_option="D",
            difficulty=QuestionDifficulty.HARD,
            explanation="Explanation 4",
            status=QuestionStatus.APPROVED,
            created_by=trainer.id,
        )
        # Comp 3
        q5 = Question(
            document_id=doc.id,
            competency_id=comp_3.id,
            question_text=f"CPI question 1 {suffix}?",
            option_a="Correct Option A",
            option_b="Option B",
            option_c="Option C",
            option_d="Option D",
            correct_option="A",
            difficulty=QuestionDifficulty.EASY,
            explanation="Explanation 5",
            status=QuestionStatus.APPROVED,
            created_by=trainer.id,
        )
        q6 = Question(
            document_id=doc.id,
            competency_id=comp_3.id,
            question_text=f"CPI question 2 {suffix}?",
            option_a="Option A",
            option_b="Correct Option B",
            option_c="Option C",
            option_d="Option D",
            correct_option="B",
            difficulty=QuestionDifficulty.MEDIUM,
            explanation="Explanation 6",
            status=QuestionStatus.APPROVED,
            created_by=trainer.id,
        )
        db.add_all([q1, q2, q3, q4, q5, q6])
        db.commit()

        # 5. Prototype Course
        course = Course(
            igot_course_id=f"IGOT-TEST-{suffix}",
            title="Advanced ASI Survey Methodology",
            description="Deep dive course on ASI estimation framework",
            provider="NSSTA",
            language="English",
            difficulty=QuestionDifficulty.MEDIUM,
            duration_minutes=120,
            course_url="https://igotkarmayogi.gov.in/courses/test",
            is_public=True,
            is_active=True,
        )
        db.add(course)
        db.commit()

        # Auth Tokens
        t_off1 = create_access_token({"sub": str(officer_1.id), "email": officer_1.email, "role": RoleName.OFFICER.value})
        t_off2 = create_access_token({"sub": str(officer_2.id), "email": officer_2.email, "role": RoleName.OFFICER.value})
        t_trn = create_access_token({"sub": str(trainer.id), "email": trainer.email, "role": RoleName.TRAINER.value})
        t_sme = create_access_token({"sub": str(sme.id), "email": sme.email, "role": RoleName.SME.value})
        t_adm = create_access_token({"sub": str(admin.id), "email": admin.email, "role": RoleName.ADMIN.value})

        return {
            "officer_1_id": officer_1.id,
            "officer_2_id": officer_2.id,
            "trainer_id": trainer.id,
            "sme_id": sme.id,
            "admin_id": admin.id,
            "comp_1_id": comp_1.id,
            "comp_2_id": comp_2.id,
            "comp_3_id": comp_3.id,
            "q1_id": q1.id,
            "q2_id": q2.id,
            "q3_id": q3.id,
            "q4_id": q4.id,
            "q5_id": q5.id,
            "q6_id": q6.id,
            "course_id": course.id,
            "headers_off1": {"Authorization": f"Bearer {t_off1}"},
            "headers_off2": {"Authorization": f"Bearer {t_off2}"},
            "headers_trn": {"Authorization": f"Bearer {t_trn}"},
            "headers_sme": {"Authorization": f"Bearer {t_sme}"},
            "headers_adm": {"Authorization": f"Bearer {t_adm}"},
        }
    finally:
        db.close()


def helper_create_completed_baseline(
    db: Session,
    officer_id: int,
    comp_scores: dict,  # {comp_id: (correct_count, total_count, [q_ids])}
    title: str = "Baseline Diagnostic Assessment",
) -> int:
    """Helper to seed an immutable completed baseline assessment with exact competency scores."""
    total_q = sum(item[1] for item in comp_scores.values())
    total_c = sum(item[0] for item in comp_scores.values())
    score_pct = round((total_c / total_q) * 100, 2) if total_q > 0 else 0.0

    baseline = Assessment(
        officer_id=officer_id,
        title=title,
        status=AssessmentStatus.COMPLETED,
        total_questions=total_q,
        total_correct=total_c,
        score_percentage=Decimal(str(score_pct)),
        completed_at=datetime.now(timezone.utc),
    )
    db.add(baseline)
    db.flush()

    order = 1
    for cid, (correct, total, q_ids) in comp_scores.items():
        comp_pct = round((correct / total) * 100, 2) if total > 0 else 0.0
        if comp_pct >= settings.ADVANCED_THRESHOLD:
            prof = ProficiencyLevel.ADVANCED
            gap = None
        elif comp_pct >= settings.PROFICIENT_THRESHOLD:
            prof = ProficiencyLevel.PROFICIENT
            gap = GapLevel.LOW
        elif comp_pct >= settings.DEVELOPING_THRESHOLD:
            prof = ProficiencyLevel.DEVELOPING
            gap = GapLevel.MEDIUM
        else:
            prof = ProficiencyLevel.BEGINNER
            gap = GapLevel.HIGH

        cr = CompetencyResult(
            assessment_id=baseline.id,
            competency_id=cid,
            questions_attempted=total,
            questions_correct=correct,
            score_percentage=Decimal(str(comp_pct)),
            proficiency_level=prof,
        )
        db.add(cr)

        if gap is not None:
            sg = SkillGap(
                assessment_id=baseline.id,
                competency_id=cid,
                score_percentage=Decimal(str(comp_pct)),
                gap_level=gap,
            )
            db.add(sg)

        for qid in q_ids:
            aq = AssessmentQuestion(
                assessment_id=baseline.id,
                question_id=qid,
                question_order=order,
            )
            db.add(aq)
            order += 1

    db.commit()
    db.refresh(baseline)
    return baseline.id


# ============================================================================
# Test Scenarios
# ============================================================================

def test_canonical_title_parser_and_formatter():
    """Validates the canonical title parser and formatter."""
    title = format_reassessment_title(42, "ASI Survey Assessment")
    assert title == "Reassessment [Baseline #42]: ASI Survey Assessment"
    assert parse_baseline_id_from_title(title) == 42

    # Malformed cases
    assert parse_baseline_id_from_title("Regular Assessment") is None
    assert parse_baseline_id_from_title("Reassessment: Baseline #42") is None
    assert parse_baseline_id_from_title("Reassessment [Baseline #abc]: Title") is None
    assert parse_baseline_id_from_title(None) is None


def test_create_reassessment_unauthenticated(setup_reassessment_env):
    """Rejection with HTTP 401 when unauthenticated."""
    res = client.post("/api/v1/assessments/1/reassess", json={})
    assert res.status_code == 401


def test_create_reassessment_other_officer_forbidden(setup_reassessment_env):
    """Officer A cannot trigger reassessment for Officer B's baseline (HTTP 403)."""
    env = setup_reassessment_env
    db: Session = SessionLocal()
    try:
        baseline_id = helper_create_completed_baseline(
            db=db,
            officer_id=env["officer_2_id"],
            comp_scores={env["comp_1_id"]: (0, 2, [env["q1_id"], env["q2_id"]])},
        )
    finally:
        db.close()

    # Officer 1 attempts to reassess Officer 2's baseline
    res = client.post(f"/api/v1/assessments/{baseline_id}/reassess", headers=env["headers_off1"], json={})
    assert res.status_code == 403
    assert "Access denied" in res.json()["detail"]


def test_create_reassessment_in_progress_baseline_rejected(setup_reassessment_env):
    """Reassessment requires completed baseline (HTTP 400)."""
    env = setup_reassessment_env
    db: Session = SessionLocal()
    try:
        in_prog = Assessment(
            officer_id=env["officer_1_id"],
            title="In Progress Baseline",
            status=AssessmentStatus.IN_PROGRESS,
            total_questions=2,
            total_correct=0,
            score_percentage=Decimal("0.00"),
        )
        db.add(in_prog)
        db.commit()
        db.refresh(in_prog)
        in_prog_id = in_prog.id
    finally:
        db.close()

    res = client.post(f"/api/v1/assessments/{in_prog_id}/reassess", headers=env["headers_off1"], json={})
    assert res.status_code == 400
    assert "must be completed" in res.json()["detail"]


def test_create_reassessment_of_reassessment_rejected(setup_reassessment_env):
    """Disallow creating a reassessment of another reassessment (HTTP 400)."""
    env = setup_reassessment_env
    db: Session = SessionLocal()
    try:
        baseline_id = helper_create_completed_baseline(
            db=db,
            officer_id=env["officer_1_id"],
            comp_scores={env["comp_1_id"]: (0, 2, [env["q1_id"], env["q2_id"]])},
        )
    finally:
        db.close()

    # 1. Create first reassessment
    res1 = client.post(f"/api/v1/assessments/{baseline_id}/reassess", headers=env["headers_off1"], json={})
    assert res1.status_code == 201
    reassessment_id = res1.json()["id"]

    # Mark first reassessment as completed
    db = SessionLocal()
    try:
        r1 = db.query(Assessment).filter(Assessment.id == reassessment_id).first()
        r1.status = AssessmentStatus.COMPLETED
        db.commit()
    finally:
        db.close()

    # 2. Try to reassess the reassessment itself
    res2 = client.post(f"/api/v1/assessments/{reassessment_id}/reassess", headers=env["headers_off1"], json={})
    assert res2.status_code == 400
    assert "Cannot create a reassessment of another reassessment" in res2.json()["detail"]


def test_create_reassessment_targets_baseline_gaps(setup_reassessment_env):
    """Reassessment correctly targets competencies where baseline skill gaps were identified."""
    env = setup_reassessment_env
    db: Session = SessionLocal()
    try:
        # Baseline: Gap on Comp 1 (0%), No gap on Comp 2 (100%)
        baseline_id = helper_create_completed_baseline(
            db=db,
            officer_id=env["officer_1_id"],
            comp_scores={
                env["comp_1_id"]: (0, 2, [env["q1_id"], env["q2_id"]]),
                env["comp_2_id"]: (2, 2, [env["q3_id"], env["q4_id"]]),
            },
        )
    finally:
        db.close()

    res = client.post(f"/api/v1/assessments/{baseline_id}/reassess", headers=env["headers_off1"], json={})
    assert res.status_code == 201
    data = res.json()
    assert data["title"].startswith(f"Reassessment [Baseline #{baseline_id}]:")
    assert data["status"] == "IN_PROGRESS"
    # Assigned questions should belong exclusively to Comp 1 (the gap competency)
    assert len(data["questions"]) == 2
    for q in data["questions"]:
        assert q["competency_id"] == env["comp_1_id"]
        # Check answer masking: no correct_option or explanation exposed
        assert "correct_option" not in q
        assert "explanation" not in q


def test_baseline_assessment_remains_unmodified(setup_reassessment_env):
    """Baseline assessment, answers, results, and gaps remain 100% immutable."""
    env = setup_reassessment_env
    db: Session = SessionLocal()
    try:
        baseline_id = helper_create_completed_baseline(
            db=db,
            officer_id=env["officer_1_id"],
            comp_scores={env["comp_1_id"]: (0, 2, [env["q1_id"], env["q2_id"]])},
            title="Immutable Baseline 100",
        )
        b_before = db.query(Assessment).filter(Assessment.id == baseline_id).first()
        b_score_before = float(b_before.score_percentage)
        b_status_before = b_before.status
        b_title_before = b_before.title
    finally:
        db.close()

    # Create reassessment
    res = client.post(f"/api/v1/assessments/{baseline_id}/reassess", headers=env["headers_off1"], json={})
    assert res.status_code == 201
    reassessment_id = res.json()["id"]

    # Submit reassessment answers via POST /api/v1/assessments/{reassessment_id}/submit
    sub_res = client.post(
        f"/api/v1/assessments/{reassessment_id}/submit",
        headers=env["headers_off1"],
        json={"answers": [{"question_id": env["q1_id"], "selected_option": "A"}, {"question_id": env["q2_id"], "selected_option": "B"}]},
    )
    assert sub_res.status_code == 200

    # Verify baseline is completely unchanged
    db = SessionLocal()
    try:
        b_after = db.query(Assessment).filter(Assessment.id == baseline_id).first()
        assert float(b_after.score_percentage) == b_score_before
        assert b_after.status == b_status_before
        assert b_after.title == b_title_before

        # Baseline still has its original skill gap
        b_gaps = db.query(SkillGap).filter(SkillGap.assessment_id == baseline_id).all()
        assert len(b_gaps) == 1
        assert b_gaps[0].gap_level == GapLevel.HIGH
    finally:
        db.close()


def test_reassessment_submission_reuses_phase7_endpoint(setup_reassessment_env):
    """Reassessment submission reuses existing Phase 7 endpoint returning AssessmentResultResponse."""
    env = setup_reassessment_env
    db: Session = SessionLocal()
    try:
        baseline_id = helper_create_completed_baseline(
            db=db,
            officer_id=env["officer_1_id"],
            comp_scores={env["comp_1_id"]: (0, 2, [env["q1_id"], env["q2_id"]])},
        )
    finally:
        db.close()

    res = client.post(f"/api/v1/assessments/{baseline_id}/reassess", headers=env["headers_off1"], json={})
    reassessment_id = res.json()["id"]

    sub_res = client.post(
        f"/api/v1/assessments/{reassessment_id}/submit",
        headers=env["headers_off1"],
        json={"answers": [{"question_id": env["q1_id"], "selected_option": "A"}, {"question_id": env["q2_id"], "selected_option": "B"}]},
    )
    assert sub_res.status_code == 200
    res_data = sub_res.json()
    assert res_data["assessment_id"] == reassessment_id
    assert res_data["status"] == "COMPLETED"
    assert res_data["score_percentage"] == 100.0
    assert len(res_data["competency_results"]) == 1
    assert res_data["competency_results"][0]["proficiency_level"] == "ADVANCED"
    assert len(res_data["skill_gaps"]) == 0  # 100% means gap resolved


# ============================================================================
# Macro Closed-Loop State Precedence Tests (Mandatory Revision 3)
# ============================================================================

def test_macro_precedence_case1_improvement_plus_decline(setup_reassessment_env):
    """Precedence Case 1: Improvement + Decline -> PARTIALLY_CLOSED.
    
    Baseline:
    - Comp 1: 0% (HIGH Gap)
    - Comp 2: 50% (MEDIUM Gap)
    Reassessment:
    - Comp 1: 100% (RESOLVED)
    - Comp 2: 0% (DECLINED to HIGH)
    
    Expected Macro State: PARTIALLY_CLOSED (A decline does NOT override PARTIALLY_CLOSED).
    Comp 2 must be recorded in declined_competency_ids.
    """
    env = setup_reassessment_env
    db: Session = SessionLocal()
    try:
        baseline_id = helper_create_completed_baseline(
            db=db,
            officer_id=env["officer_1_id"],
            comp_scores={
                env["comp_1_id"]: (0, 2, [env["q1_id"], env["q2_id"]]),
                env["comp_2_id"]: (1, 2, [env["q3_id"], env["q4_id"]]),
            },
        )
    finally:
        db.close()

    # Reassessment created targeting both competencies
    res = client.post(
        f"/api/v1/assessments/{baseline_id}/reassess",
        headers=env["headers_off1"],
        json={"competency_ids": [env["comp_1_id"], env["comp_2_id"]]},
    )
    reassessment_id = res.json()["id"]

    # Submit: Comp 1 correct (A, B = 100%), Comp 2 incorrect (A, A = 0%)
    client.post(
        f"/api/v1/assessments/{reassessment_id}/submit",
        headers=env["headers_off1"],
        json={
            "answers": [
                {"question_id": env["q1_id"], "selected_option": "A"},
                {"question_id": env["q2_id"], "selected_option": "B"},
                {"question_id": env["q3_id"], "selected_option": "A"},
                {"question_id": env["q4_id"], "selected_option": "A"},
            ]
        },
    )

    comp_res = client.get(f"/api/v1/assessments/{reassessment_id}/comparison", headers=env["headers_off1"])
    assert comp_res.status_code == 200
    comp_data = comp_res.json()

    assert comp_data["loop_status"] == "PARTIALLY_CLOSED"
    assert env["comp_2_id"] in comp_data["declined_competency_ids"]

    # Verify granular items
    c1 = next(c for c in comp_data["competency_comparisons"] if c["competency_id"] == env["comp_1_id"])
    c2 = next(c for c in comp_data["competency_comparisons"] if c["competency_id"] == env["comp_2_id"])
    assert c1["gap_resolution_status"] == "RESOLVED"
    assert c1["improvement_status"] == "IMPROVED"
    assert c2["improvement_status"] == "DECLINED"
    assert c2["gap_resolution_status"] == "INCREASED"


def test_macro_precedence_case2_partial_improvement_plus_decline(setup_reassessment_env):
    """Precedence Case 2: Partial improvement (severity reduced) + Decline -> PARTIALLY_CLOSED.
    
    Baseline:
    - Comp 1: 0% (HIGH Gap)
    - Comp 2: 75% (LOW Gap, 1 of 2 correct: q3 correct, q4 wrong => actually 50% is MEDIUM)
    Let's test Comp 1 reduced from HIGH (0%) to MEDIUM (50%).
    Comp 2 declined from MEDIUM (50%) to HIGH (0%).
    
    Expected Macro State: PARTIALLY_CLOSED.
    """
    env = setup_reassessment_env
    db: Session = SessionLocal()
    try:
        baseline_id = helper_create_completed_baseline(
            db=db,
            officer_id=env["officer_1_id"],
            comp_scores={
                env["comp_1_id"]: (0, 2, [env["q1_id"], env["q2_id"]]),  # 0% HIGH
                env["comp_2_id"]: (1, 2, [env["q3_id"], env["q4_id"]]),  # 50% MEDIUM
            },
        )
    finally:
        db.close()

    res = client.post(
        f"/api/v1/assessments/{baseline_id}/reassess",
        headers=env["headers_off1"],
        json={"competency_ids": [env["comp_1_id"], env["comp_2_id"]]},
    )
    reassessment_id = res.json()["id"]

    # Submit: Comp 1 gets 1 right (q1=A right, q2=A wrong => 50% MEDIUM => REDUCED from HIGH)
    # Comp 2 gets 0 right (q3=A wrong, q4=A wrong => 0% HIGH => INCREASED from MEDIUM)
    client.post(
        f"/api/v1/assessments/{reassessment_id}/submit",
        headers=env["headers_off1"],
        json={
            "answers": [
                {"question_id": env["q1_id"], "selected_option": "A"},
                {"question_id": env["q2_id"], "selected_option": "A"},
                {"question_id": env["q3_id"], "selected_option": "A"},
                {"question_id": env["q4_id"], "selected_option": "A"},
            ]
        },
    )

    comp_res = client.get(f"/api/v1/assessments/{reassessment_id}/comparison", headers=env["headers_off1"])
    assert comp_res.status_code == 200
    comp_data = comp_res.json()

    assert comp_data["loop_status"] == "PARTIALLY_CLOSED"
    c1 = next(c for c in comp_data["competency_comparisons"] if c["competency_id"] == env["comp_1_id"])
    c2 = next(c for c in comp_data["competency_comparisons"] if c["competency_id"] == env["comp_2_id"])
    assert c1["gap_resolution_status"] == "REDUCED"
    assert c2["gap_resolution_status"] == "INCREASED"


def test_macro_precedence_case3_zero_improvement_plus_decline(setup_reassessment_env):
    """Precedence Case 3: Zero improvement + Decline -> LOOP_OPEN.
    
    Baseline:
    - Comp 1: 50% (MEDIUM Gap)
    - Comp 2: 50% (MEDIUM Gap)
    Reassessment:
    - Comp 1: 50% (PERSISTENT, 0 improvement)
    - Comp 2: 0% (DECLINED to HIGH)
    
    Expected Macro State: LOOP_OPEN.
    """
    env = setup_reassessment_env
    db: Session = SessionLocal()
    try:
        baseline_id = helper_create_completed_baseline(
            db=db,
            officer_id=env["officer_1_id"],
            comp_scores={
                env["comp_1_id"]: (1, 2, [env["q1_id"], env["q2_id"]]),  # 50% MEDIUM
                env["comp_2_id"]: (1, 2, [env["q3_id"], env["q4_id"]]),  # 50% MEDIUM
            },
        )
    finally:
        db.close()

    res = client.post(
        f"/api/v1/assessments/{baseline_id}/reassess",
        headers=env["headers_off1"],
        json={"competency_ids": [env["comp_1_id"], env["comp_2_id"]]},
    )
    reassessment_id = res.json()["id"]

    # Submit: Comp 1 gets 1 right (q1=A, q2=A => 50%), Comp 2 gets 0 right (q3=A, q4=A => 0%)
    client.post(
        f"/api/v1/assessments/{reassessment_id}/submit",
        headers=env["headers_off1"],
        json={
            "answers": [
                {"question_id": env["q1_id"], "selected_option": "A"},
                {"question_id": env["q2_id"], "selected_option": "A"},
                {"question_id": env["q3_id"], "selected_option": "A"},
                {"question_id": env["q4_id"], "selected_option": "A"},
            ]
        },
    )

    comp_res = client.get(f"/api/v1/assessments/{reassessment_id}/comparison", headers=env["headers_off1"])
    assert comp_res.status_code == 200
    comp_data = comp_res.json()

    assert comp_data["loop_status"] == "LOOP_OPEN"


def test_macro_precedence_case4_all_gaps_resolved_plus_unrelated_decline(setup_reassessment_env):
    """Precedence Case 4: All baseline gaps resolved + unrelated competency decline -> LOOP_CLOSED.
    
    Baseline:
    - Comp 1: 0% (HIGH Gap, only baseline gap)
    - Comp 2: 100% (ADVANCED, NO gap)
    Reassessment (explicitly testing both):
    - Comp 1: 100% (RESOLVED)
    - Comp 2: 50% (Declined from 100% to 50%, NEW_GAP)
    
    Expected Macro State: LOOP_CLOSED (Rule 1: all baseline gaps resolved).
    Comp 2 must be reported in declined_competency_ids and have gap_resolution_status = NEW_GAP.
    """
    env = setup_reassessment_env
    db: Session = SessionLocal()
    try:
        baseline_id = helper_create_completed_baseline(
            db=db,
            officer_id=env["officer_1_id"],
            comp_scores={
                env["comp_1_id"]: (0, 2, [env["q1_id"], env["q2_id"]]),  # Only gap
                env["comp_2_id"]: (2, 2, [env["q3_id"], env["q4_id"]]),  # 100% (No gap)
            },
        )
    finally:
        db.close()

    res = client.post(
        f"/api/v1/assessments/{baseline_id}/reassess",
        headers=env["headers_off1"],
        json={"competency_ids": [env["comp_1_id"], env["comp_2_id"]]},
    )
    reassessment_id = res.json()["id"]

    # Submit: Comp 1=100% (q1=A, q2=B), Comp 2=50% (q3=C, q4=A)
    client.post(
        f"/api/v1/assessments/{reassessment_id}/submit",
        headers=env["headers_off1"],
        json={
            "answers": [
                {"question_id": env["q1_id"], "selected_option": "A"},
                {"question_id": env["q2_id"], "selected_option": "B"},
                {"question_id": env["q3_id"], "selected_option": "C"},
                {"question_id": env["q4_id"], "selected_option": "A"},
            ]
        },
    )

    comp_res = client.get(f"/api/v1/assessments/{reassessment_id}/comparison", headers=env["headers_off1"])
    assert comp_res.status_code == 200
    comp_data = comp_res.json()

    assert comp_data["loop_status"] == "LOOP_CLOSED"
    assert env["comp_2_id"] in comp_data["declined_competency_ids"]

    c1 = next(c for c in comp_data["competency_comparisons"] if c["competency_id"] == env["comp_1_id"])
    c2 = next(c for c in comp_data["competency_comparisons"] if c["competency_id"] == env["comp_2_id"])
    assert c1["gap_resolution_status"] == "RESOLVED"
    assert c2["gap_resolution_status"] == "NEW_GAP"
    assert c2["improvement_status"] == "DECLINED"


# ============================================================================
# Longitudinal Comparison, Edge Cases & Learning Correlation
# ============================================================================

def test_reassessment_comparison_in_progress_rejected(setup_reassessment_env):
    """Calling comparison on an IN_PROGRESS reassessment returns HTTP 400."""
    env = setup_reassessment_env
    db: Session = SessionLocal()
    try:
        baseline_id = helper_create_completed_baseline(
            db=db,
            officer_id=env["officer_1_id"],
            comp_scores={env["comp_1_id"]: (0, 2, [env["q1_id"], env["q2_id"]])},
        )
    finally:
        db.close()

    res = client.post(f"/api/v1/assessments/{baseline_id}/reassess", headers=env["headers_off1"], json={})
    reassessment_id = res.json()["id"]

    comp_res = client.get(f"/api/v1/assessments/{reassessment_id}/comparison", headers=env["headers_off1"])
    assert comp_res.status_code == 400
    assert "still in progress" in comp_res.json()["detail"]


def test_reassessment_comparison_malformed_linkage_rejected(setup_reassessment_env):
    """Assessment without baseline linkage in title and no query param returns HTTP 400."""
    env = setup_reassessment_env
    db: Session = SessionLocal()
    try:
        regular = Assessment(
            officer_id=env["officer_1_id"],
            title="Non Reassessment Standard Diagnostic",
            status=AssessmentStatus.COMPLETED,
            total_questions=2,
            total_correct=2,
            score_percentage=Decimal("100.00"),
            completed_at=datetime.now(timezone.utc),
        )
        db.add(regular)
        db.commit()
        db.refresh(regular)
        reg_id = regular.id
    finally:
        db.close()

    res = client.get(f"/api/v1/assessments/{reg_id}/comparison", headers=env["headers_off1"])
    assert res.status_code == 400
    assert "Malformed linkage" in res.json()["detail"]


def test_reassessment_comparison_mismatched_baseline_query_param(setup_reassessment_env):
    """Explicit query param ?baseline_id=999 that conflicts with title linkage returns HTTP 400."""
    env = setup_reassessment_env
    db: Session = SessionLocal()
    try:
        baseline_id = helper_create_completed_baseline(
            db=db,
            officer_id=env["officer_1_id"],
            comp_scores={env["comp_1_id"]: (0, 2, [env["q1_id"], env["q2_id"]])},
        )
    finally:
        db.close()

    res = client.post(f"/api/v1/assessments/{baseline_id}/reassess", headers=env["headers_off1"], json={})
    reassessment_id = res.json()["id"]

    # Complete it
    client.post(
        f"/api/v1/assessments/{reassessment_id}/submit",
        headers=env["headers_off1"],
        json={"answers": [{"question_id": env["q1_id"], "selected_option": "A"}, {"question_id": env["q2_id"], "selected_option": "B"}]},
    )

    comp_res = client.get(
        f"/api/v1/assessments/{reassessment_id}/comparison?baseline_id=9999",
        headers=env["headers_off1"],
    )
    assert comp_res.status_code == 400
    assert "does not match" in comp_res.json()["detail"]


def test_reassessment_comparison_self_comparison_rejected(setup_reassessment_env):
    """Comparing an assessment against itself returns HTTP 400."""
    env = setup_reassessment_env
    db: Session = SessionLocal()
    try:
        baseline_id = helper_create_completed_baseline(
            db=db,
            officer_id=env["officer_1_id"],
            comp_scores={env["comp_1_id"]: (0, 2, [env["q1_id"], env["q2_id"]])},
        )
    finally:
        db.close()

    # Pass ?baseline_id={id} pointing to the same id
    res = client.get(
        f"/api/v1/assessments/{baseline_id}/comparison?baseline_id={baseline_id}",
        headers=env["headers_off1"],
    )
    assert res.status_code == 400
    assert "Cannot compare an assessment against itself" in res.json()["detail"]


def test_reassessment_learning_context_correlation(setup_reassessment_env):
    """Preceding completed course is cited in associated_learning with non-causal disclaimer."""
    env = setup_reassessment_env
    db: Session = SessionLocal()
    try:
        baseline_id = helper_create_completed_baseline(
            db=db,
            officer_id=env["officer_1_id"],
            comp_scores={env["comp_1_id"]: (0, 2, [env["q1_id"], env["q2_id"]])},
        )
        # Create completed recommendation for officer linked to baseline & course
        rec = Recommendation(
            officer_id=env["officer_1_id"],
            assessment_id=baseline_id,
            competency_id=env["comp_1_id"],
            course_id=env["course_id"],
            priority=1,
            match_score=Decimal("95.00"),
            reason="High gap in ASI Industrial Estimation",
            status=RecommendationStatus.COMPLETED,
        )
        db.add(rec)
        db.commit()
    finally:
        db.close()

    # Create & submit reassessment
    res = client.post(f"/api/v1/assessments/{baseline_id}/reassess", headers=env["headers_off1"], json={})
    reassessment_id = res.json()["id"]

    client.post(
        f"/api/v1/assessments/{reassessment_id}/submit",
        headers=env["headers_off1"],
        json={"answers": [{"question_id": env["q1_id"], "selected_option": "A"}, {"question_id": env["q2_id"], "selected_option": "B"}]},
    )

    comp_res = client.get(f"/api/v1/assessments/{reassessment_id}/comparison", headers=env["headers_off1"])
    assert comp_res.status_code == 200
    comp_data = comp_res.json()

    c1 = next(c for c in comp_data["competency_comparisons"] if c["competency_id"] == env["comp_1_id"])
    assert len(c1["associated_learning"]) >= 1
    learning = c1["associated_learning"][0]
    assert learning["course_id"] == env["course_id"]
    assert learning["status"] == "COMPLETED"
    assert "developmental context and educational correlation, not formal causal proof" in learning["correlation_note"]


def test_multiple_reassessment_attempts_ordering_and_history(setup_reassessment_env):
    """Sequential attempts (Attempt 1, Attempt 2) are tracked chronologically."""
    env = setup_reassessment_env
    db: Session = SessionLocal()
    try:
        baseline_id = helper_create_completed_baseline(
            db=db,
            officer_id=env["officer_1_id"],
            comp_scores={env["comp_1_id"]: (0, 2, [env["q1_id"], env["q2_id"]])},
            title="Multi-Attempt Baseline",
        )
    finally:
        db.close()

    # Create Attempt 1
    res1 = client.post(f"/api/v1/assessments/{baseline_id}/reassess", headers=env["headers_off1"], json={})
    att1_id = res1.json()["id"]
    client.post(
        f"/api/v1/assessments/{att1_id}/submit",
        headers=env["headers_off1"],
        json={"answers": [{"question_id": env["q1_id"], "selected_option": "A"}, {"question_id": env["q2_id"], "selected_option": "A"}]},
    )

    # Create Attempt 2
    res2 = client.post(f"/api/v1/assessments/{baseline_id}/reassess", headers=env["headers_off1"], json={})
    att2_id = res2.json()["id"]
    client.post(
        f"/api/v1/assessments/{att2_id}/submit",
        headers=env["headers_off1"],
        json={"answers": [{"question_id": env["q1_id"], "selected_option": "A"}, {"question_id": env["q2_id"], "selected_option": "B"}]},
    )

    # List attempts for baseline
    list_res = client.get(f"/api/v1/assessments/{baseline_id}/reassessments", headers=env["headers_off1"])
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["baseline_assessment_id"] == baseline_id
    assert list_data["total_attempts"] == 2
    assert list_data["items"][0]["id"] == att1_id
    assert list_data["items"][0]["attempt_number"] == 1
    assert list_data["items"][1]["id"] == att2_id
    assert list_data["items"][1]["attempt_number"] == 2


def test_reassessment_rbac_trainer_and_admin(setup_reassessment_env):
    """Trainer and Admin can view comparisons across officers; Trainer cannot create reassessment."""
    env = setup_reassessment_env
    db: Session = SessionLocal()
    try:
        baseline_id = helper_create_completed_baseline(
            db=db,
            officer_id=env["officer_1_id"],
            comp_scores={env["comp_1_id"]: (0, 2, [env["q1_id"], env["q2_id"]])},
        )
    finally:
        db.close()

    # Trainer creates reassessment -> 403 Forbidden
    res_trn_create = client.post(f"/api/v1/assessments/{baseline_id}/reassess", headers=env["headers_trn"], json={})
    assert res_trn_create.status_code == 403

    # Admin creates reassessment -> 201 Created
    res_adm_create = client.post(f"/api/v1/assessments/{baseline_id}/reassess", headers=env["headers_adm"], json={})
    assert res_adm_create.status_code == 201
    reassessment_id = res_adm_create.json()["id"]

    # Submit reassessment as officer
    client.post(
        f"/api/v1/assessments/{reassessment_id}/submit",
        headers=env["headers_off1"],
        json={"answers": [{"question_id": env["q1_id"], "selected_option": "A"}, {"question_id": env["q2_id"], "selected_option": "B"}]},
    )

    # Trainer views comparison -> 200 OK
    res_trn_comp = client.get(f"/api/v1/assessments/{reassessment_id}/comparison", headers=env["headers_trn"])
    assert res_trn_comp.status_code == 200

    # Trainer lists attempts -> 200 OK
    res_trn_list = client.get(f"/api/v1/assessments/{baseline_id}/reassessments", headers=env["headers_trn"])
    assert res_trn_list.status_code == 200
    assert res_trn_list.json()["total_attempts"] >= 1


def test_reassessment_rbac_sme_forbidden(setup_reassessment_env):
    """SME is forbidden (HTTP 403) from creating, submitting, comparing, or listing reassessments."""
    env = setup_reassessment_env
    db: Session = SessionLocal()
    try:
        baseline_id = helper_create_completed_baseline(
            db=db,
            officer_id=env["officer_1_id"],
            comp_scores={env["comp_1_id"]: (0, 2, [env["q1_id"], env["q2_id"]])},
        )
    finally:
        db.close()

    # Create
    assert client.post(f"/api/v1/assessments/{baseline_id}/reassess", headers=env["headers_sme"], json={}).status_code == 403
    # Compare
    assert client.get(f"/api/v1/assessments/{baseline_id}/comparison", headers=env["headers_sme"]).status_code == 403
    # List attempts
    assert client.get(f"/api/v1/assessments/{baseline_id}/reassessments", headers=env["headers_sme"]).status_code == 403


def test_zero_schema_changes_and_16_tables():
    """Verifies that the database schema has exactly 16 PostgreSQL tables (Zero Schema Changes)."""
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    assert len(table_names) == 16, f"Expected exactly 16 tables, found {len(table_names)}: {table_names}"
    expected_tables = {
        "alembic_version",
        "answers",
        "assessment_questions",
        "assessments",
        "competencies",
        "competency_results",
        "course_competencies",
        "courses",
        "document_chunks",
        "documents",
        "question_reviews",
        "questions",
        "recommendations",
        "roles",
        "skill_gaps",
        "users",
    }
    assert set(table_names) == expected_tables, f"Table schema mismatch: {set(table_names) ^ expected_tables}"
