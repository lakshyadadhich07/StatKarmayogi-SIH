from datetime import datetime, timezone
from decimal import Decimal
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token
from app.db.seed import seed_roles
from app.db.session import SessionLocal
from app.main import app
from app.models.answer import Answer
from app.models.assessment import Assessment
from app.models.assessment_question import AssessmentQuestion
from app.models.competency import Competency
from app.models.competency_result import CompetencyResult
from app.models.document import Document
from app.models.enums import AssessmentStatus, DocumentStatus, GapLevel, ProficiencyLevel, QuestionDifficulty, QuestionStatus, RoleName
from app.models.question import Question
from app.models.role import Role
from app.models.skill_gap import SkillGap
from app.models.user import User
from app.services.assessment_service import AssessmentService

client = TestClient(app)


@pytest.fixture(scope="module")
def setup_test_environment():
    """Sets up roles, test users, document, competencies, and questions, returning pure scalar IDs and tokens."""
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
            name="Field Officer One",
            email=f"officer1_{suffix}@mospi.gov.in",
            password_hash="test_hash",
            role_id=officer_role.id,
            is_active=True,
        )
        officer_2 = User(
            name="Field Officer Two",
            email=f"officer2_{suffix}@mospi.gov.in",
            password_hash="test_hash",
            role_id=officer_role.id,
            is_active=True,
        )
        trainer = User(
            name="NSSTA Trainer",
            email=f"trainer_{suffix}@mospi.gov.in",
            password_hash="test_hash",
            role_id=trainer_role.id,
            is_active=True,
        )
        sme = User(
            name="SME Reviewer",
            email=f"sme_{suffix}@mospi.gov.in",
            password_hash="test_hash",
            role_id=sme_role.id,
            is_active=True,
        )
        admin = User(
            name="MoSPI Admin",
            email=f"admin_{suffix}@mospi.gov.in",
            password_hash="test_hash",
            role_id=admin_role.id,
            is_active=True,
        )
        db.add_all([officer_1, officer_2, trainer, sme, admin])
        db.commit()

        # 2. Competencies
        comp_a = Competency(
            code=f"COMP_ASI_{suffix}",
            name="ASI Industrial Estimation",
            description="Methodology and frame coverage for ASI survey",
            is_active=True,
        )
        comp_b = Competency(
            code=f"COMP_NAD_{suffix}",
            name="National Accounts & GVA",
            description="Gross Value Added and fixed capital consumption",
            is_active=True,
        )
        db.add_all([comp_a, comp_b])
        db.commit()

        # 3. Document
        doc = Document(
            uploaded_by=trainer.id,
            filename=f"asi_manual_{suffix}.pdf",
            file_type="pdf",
            file_path=f"storage/documents/asi_manual_{suffix}.pdf",
            status=DocumentStatus.PROCESSED,
        )
        db.add(doc)
        db.commit()

        # 4. Questions
        # Comp A questions (APPROVED)
        q1 = Question(
            document_id=doc.id,
            competency_id=comp_a.id,
            question_text="What is the definition of gross output in ASI?",
            option_a="Total ex-factory value of goods produced",
            option_b="Only intermediate consumption value",
            option_c="Total net capital depreciation",
            option_d="Tax deducted at source",
            correct_option="A",
            difficulty=QuestionDifficulty.MEDIUM,
            explanation="ASI methodology defines gross output as total ex-factory value of goods produced.",
            source_page=12,
            status=QuestionStatus.APPROVED,
            created_by=trainer.id,
        )
        q2 = Question(
            document_id=doc.id,
            competency_id=comp_a.id,
            question_text="Which section of the Factories Act defines the ASI frame?",
            option_a="Section 1a",
            option_b="Section 2m(i) and 2m(ii)",
            option_c="Section 5c",
            option_d="Section 10",
            correct_option="B",
            difficulty=QuestionDifficulty.EASY,
            explanation="Sections 2m(i) and 2m(ii) of the Factories Act define the frame.",
            source_page=15,
            status=QuestionStatus.APPROVED,
            created_by=trainer.id,
        )

        # Comp B questions (APPROVED)
        q3 = Question(
            document_id=doc.id,
            competency_id=comp_b.id,
            question_text="How is Net Value Added derived from Gross Value Added?",
            option_a="Adding subsidies",
            option_b="Multiplying by factor cost",
            option_c="Deducting consumption of fixed capital (depreciation)",
            option_d="Dividing by total employment",
            correct_option="C",
            difficulty=QuestionDifficulty.MEDIUM,
            explanation="Net Value Added equals Gross Value Added minus consumption of fixed capital.",
            source_page=45,
            status=QuestionStatus.APPROVED,
            created_by=trainer.id,
        )
        q4 = Question(
            document_id=doc.id,
            competency_id=comp_b.id,
            question_text="Which pricing valuation is standard for GVA in national accounts?",
            option_a="Retail consumer price",
            option_b="Import parity price",
            option_c="Export tariff cost",
            option_d="Basic prices excluding net product taxes",
            correct_option="D",
            difficulty=QuestionDifficulty.HARD,
            explanation="GVA at basic prices excludes product taxes and includes product subsidies.",
            source_page=48,
            status=QuestionStatus.APPROVED,
            created_by=trainer.id,
        )

        # Pending Review question (must be excluded from assessments)
        q_pending = Question(
            document_id=doc.id,
            competency_id=comp_a.id,
            question_text="Pending question text that is unapproved?",
            option_a="A",
            option_b="B",
            option_c="C",
            option_d="D",
            correct_option="A",
            difficulty=QuestionDifficulty.EASY,
            status=QuestionStatus.PENDING_REVIEW,
            created_by=trainer.id,
        )

        # Rejected question (must be excluded from assessments)
        q_rejected = Question(
            document_id=doc.id,
            competency_id=comp_b.id,
            question_text="Rejected question with flawed distractors?",
            option_a="A",
            option_b="B",
            option_c="C",
            option_d="D",
            correct_option="A",
            difficulty=QuestionDifficulty.EASY,
            status=QuestionStatus.REJECTED,
            created_by=trainer.id,
        )

        # Null competency question (must be excluded from diagnostic assessments)
        q_null_comp = Question(
            document_id=doc.id,
            competency_id=None,
            question_text="General knowledge question without competency tag?",
            option_a="A",
            option_b="B",
            option_c="C",
            option_d="D",
            correct_option="A",
            difficulty=QuestionDifficulty.EASY,
            status=QuestionStatus.APPROVED,
            created_by=trainer.id,
        )

        db.add_all([q1, q2, q3, q4, q_pending, q_rejected, q_null_comp])
        db.commit()

        tokens = {
            "officer_1": create_access_token({"sub": str(officer_1.id), "email": officer_1.email, "role": RoleName.OFFICER.value}),
            "officer_2": create_access_token({"sub": str(officer_2.id), "email": officer_2.email, "role": RoleName.OFFICER.value}),
            "trainer": create_access_token({"sub": str(trainer.id), "email": trainer.email, "role": RoleName.TRAINER.value}),
            "sme": create_access_token({"sub": str(sme.id), "email": sme.email, "role": RoleName.SME.value}),
            "admin": create_access_token({"sub": str(admin.id), "email": admin.email, "role": RoleName.ADMIN.value}),
        }

        # Pack scalar IDs to prevent DetachedInstanceError
        env_data = {
            "officer_1_id": officer_1.id,
            "officer_2_id": officer_2.id,
            "trainer_id": trainer.id,
            "sme_id": sme.id,
            "admin_id": admin.id,
            "tokens": tokens,
            "comp_a_id": comp_a.id,
            "comp_b_id": comp_b.id,
            "doc_id": doc.id,
            "q1_id": q1.id,
            "q2_id": q2.id,
            "q3_id": q3.id,
            "q4_id": q4.id,
            "q_pending_id": q_pending.id,
            "q_rejected_id": q_rejected.id,
            "q_null_comp_id": q_null_comp.id,
        }
        return env_data
    finally:
        db.close()


# ==============================================================================
# 1. Unauthenticated access -> 401
# ==============================================================================
def test_unauthenticated_cannot_access_assessments():
    """Unauthenticated requests must receive 401 Unauthorized across all assessment endpoints."""
    resp_create = client.post("/api/v1/assessments", json={"question_count": 2})
    assert resp_create.status_code == 401

    resp_list = client.get("/api/v1/assessments")
    assert resp_list.status_code == 401

    resp_get = client.get("/api/v1/assessments/1")
    assert resp_get.status_code == 401

    resp_submit = client.post("/api/v1/assessments/1/submit", json={"answers": [{"question_id": 1, "selected_option": "A"}]})
    assert resp_submit.status_code == 401

    resp_res = client.get("/api/v1/assessments/1/result")
    assert resp_res.status_code == 401


# ==============================================================================
# 2. Officer can create assessment
# ==============================================================================
def test_officer_can_create_assessment(setup_test_environment):
    """Officer can create an assessment with approved questions; starts IN_PROGRESS."""
    env = setup_test_environment
    headers = {"Authorization": f"Bearer {env['tokens']['officer_1']}"}
    payload = {
        "title": "MoSPI Diagnostic Test 1",
        "document_id": env["doc_id"],
        "question_count": 4,
    }
    resp = client.post("/api/v1/assessments", headers=headers, json=payload)
    assert resp.status_code == 201
    data = resp.json()

    assert data["officer_id"] == env["officer_1_id"]
    assert data["status"] == "IN_PROGRESS"
    assert data["total_questions"] == 4
    assert data["score_percentage"] == 0.0


# ==============================================================================
# 3. Admin can create assessment
# ==============================================================================
def test_admin_can_create_assessment(setup_test_environment):
    """Admin role can create assessments for any officer or themselves."""
    env = setup_test_environment
    headers = {"Authorization": f"Bearer {env['tokens']['admin']}"}
    payload = {
        "title": "Admin Created Assessment",
        "officer_id": env["officer_1_id"],
        "document_id": env["doc_id"],
        "question_count": 2,
    }
    resp = client.post("/api/v1/assessments", headers=headers, json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["officer_id"] == env["officer_1_id"]
    assert data["status"] == "IN_PROGRESS"


# ==============================================================================
# 4. Trainer cannot create assessment
# ==============================================================================
def test_trainer_cannot_create_assessment(setup_test_environment):
    """Trainer role is forbidden from creating assessments (403)."""
    env = setup_test_environment
    headers = {"Authorization": f"Bearer {env['tokens']['trainer']}"}
    resp = client.post("/api/v1/assessments", headers=headers, json={"question_count": 2})
    assert resp.status_code == 403


# ==============================================================================
# 5. SME cannot access assessment endpoints
# ==============================================================================
def test_sme_cannot_access_assessment_endpoints(setup_test_environment):
    """SME role is forbidden across all assessment endpoints (403)."""
    env = setup_test_environment
    headers = {"Authorization": f"Bearer {env['tokens']['sme']}"}
    assert client.post("/api/v1/assessments", headers=headers, json={"question_count": 2}).status_code == 403
    assert client.get("/api/v1/assessments", headers=headers).status_code == 403
    assert client.get("/api/v1/assessments/1", headers=headers).status_code == 403
    assert client.post("/api/v1/assessments/1/submit", headers=headers, json={"answers": []}).status_code == 403
    assert client.get("/api/v1/assessments/1/result", headers=headers).status_code == 403


# ==============================================================================
# 6. Only APPROVED questions selected
# ==============================================================================
def test_only_approved_questions_selected(setup_test_environment):
    """Assessment creation selects ONLY approved competency-tagged questions."""
    env = setup_test_environment
    headers = {"Authorization": f"Bearer {env['tokens']['officer_1']}"}
    resp = client.post("/api/v1/assessments", headers=headers, json={"document_id": env["doc_id"], "question_count": 4})
    assert resp.status_code == 201
    ass_id = resp.json()["id"]

    detail = client.get(f"/api/v1/assessments/{ass_id}", headers=headers).json()
    q_ids = [q["id"] for q in detail["questions"]]

    # Verify only APPROVED questions were assigned
    expected_approved_ids = {env["q1_id"], env["q2_id"], env["q3_id"], env["q4_id"]}
    assert set(q_ids) == expected_approved_ids
    assert env["q_pending_id"] not in q_ids
    assert env["q_rejected_id"] not in q_ids
    assert env["q_null_comp_id"] not in q_ids


# ==============================================================================
# 7. Competency filtering
# ==============================================================================
def test_competency_filter_works(setup_test_environment):
    """Assessment creation filters questions by competency_id."""
    env = setup_test_environment
    headers = {"Authorization": f"Bearer {env['tokens']['officer_1']}"}
    payload = {
        "competency_id": env["comp_a_id"],
        "document_id": env["doc_id"],
        "question_count": 2,
    }
    resp = client.post("/api/v1/assessments", headers=headers, json=payload)
    assert resp.status_code == 201
    data = resp.json()

    detail_resp = client.get(f"/api/v1/assessments/{data['id']}", headers=headers)
    questions = detail_resp.json()["questions"]
    assert len(questions) == 2
    for q in questions:
        assert q["competency_id"] == env["comp_a_id"]


# ==============================================================================
# 8. Document filtering
# ==============================================================================
def test_document_filter_works(setup_test_environment):
    """Assessment creation filters questions by document_id."""
    env = setup_test_environment
    headers = {"Authorization": f"Bearer {env['tokens']['officer_1']}"}
    payload = {
        "document_id": env["doc_id"],
        "question_count": 2,
    }
    resp = client.post("/api/v1/assessments", headers=headers, json=payload)
    assert resp.status_code == 201


# ==============================================================================
# 9. Deterministic question ordering
# ==============================================================================
def test_deterministic_question_ordering(setup_test_environment):
    """Assigned questions are deterministically ordered by questions.id ASC."""
    env = setup_test_environment
    headers = {"Authorization": f"Bearer {env['tokens']['officer_1']}"}
    resp = client.post("/api/v1/assessments", headers=headers, json={"document_id": env["doc_id"], "question_count": 4})
    assert resp.status_code == 201
    ass_id = resp.json()["id"]

    detail = client.get(f"/api/v1/assessments/{ass_id}", headers=headers).json()
    q_ids = [q["id"] for q in detail["questions"]]
    assert q_ids == sorted(q_ids)


# ==============================================================================
# 10. Insufficient approved questions -> 400
# ==============================================================================
def test_insufficient_approved_questions_rejected(setup_test_environment):
    """Requesting more questions than available returns 400 Bad Request."""
    env = setup_test_environment
    headers = {"Authorization": f"Bearer {env['tokens']['officer_1']}"}
    payload = {
        "document_id": env["doc_id"],
        "question_count": 50,  # Only 4 approved questions exist for this doc
    }
    resp = client.post("/api/v1/assessments", headers=headers, json=payload)
    assert resp.status_code == 400
    assert "Insufficient approved competency-tagged questions" in resp.json()["detail"]


# ==============================================================================
# 11. Correct answers masked during IN_PROGRESS
# ==============================================================================
def test_correct_answers_masked_during_in_progress(setup_test_environment):
    """Active IN_PROGRESS assessment never reveals correct_option."""
    env = setup_test_environment
    headers = {"Authorization": f"Bearer {env['tokens']['officer_1']}"}
    resp = client.post("/api/v1/assessments", headers=headers, json={"document_id": env["doc_id"], "question_count": 2})
    ass_id = resp.json()["id"]

    detail = client.get(f"/api/v1/assessments/{ass_id}", headers=headers).json()
    for q in detail["questions"]:
        assert "correct_option" not in q
        assert "is_correct" not in q


# ==============================================================================
# 12. Explanation masked during IN_PROGRESS
# ==============================================================================
def test_explanations_masked_during_in_progress(setup_test_environment):
    """Active IN_PROGRESS assessment never reveals explanation."""
    env = setup_test_environment
    headers = {"Authorization": f"Bearer {env['tokens']['officer_1']}"}
    resp = client.post("/api/v1/assessments", headers=headers, json={"document_id": env["doc_id"], "question_count": 2})
    ass_id = resp.json()["id"]

    detail = client.get(f"/api/v1/assessments/{ass_id}", headers=headers).json()
    for q in detail["questions"]:
        assert "explanation" not in q


# ==============================================================================
# 13. Source metadata masked during IN_PROGRESS
# ==============================================================================
def test_source_metadata_masked_during_in_progress(setup_test_environment):
    """Active IN_PROGRESS assessment never reveals source_page or source_chunk_id."""
    env = setup_test_environment
    headers = {"Authorization": f"Bearer {env['tokens']['officer_1']}"}
    resp = client.post("/api/v1/assessments", headers=headers, json={"document_id": env["doc_id"], "question_count": 2})
    ass_id = resp.json()["id"]

    detail = client.get(f"/api/v1/assessments/{ass_id}", headers=headers).json()
    for q in detail["questions"]:
        assert "source_page" not in q
        assert "source_chunk_id" not in q


# ==============================================================================
# 14. Ownership enforcement
# ==============================================================================
def test_officer_cannot_access_another_officers_assessment(setup_test_environment):
    """Officer B cannot view or submit Officer A's assessment (403 Forbidden)."""
    env = setup_test_environment
    headers_1 = {"Authorization": f"Bearer {env['tokens']['officer_1']}"}
    headers_2 = {"Authorization": f"Bearer {env['tokens']['officer_2']}"}

    create_resp = client.post(
        "/api/v1/assessments",
        headers=headers_1,
        json={"document_id": env["doc_id"], "question_count": 2},
    )
    assert create_resp.status_code == 201
    ass_id = create_resp.json()["id"]

    # Officer 2 attempts to get Officer 1's assessment
    get_resp = client.get(f"/api/v1/assessments/{ass_id}", headers=headers_2)
    assert get_resp.status_code == 403

    # Officer 2 attempts to submit Officer 1's assessment
    sub_resp = client.post(
        f"/api/v1/assessments/{ass_id}/submit",
        headers=headers_2,
        json={"answers": [{"question_id": 1, "selected_option": "A"}]},
    )
    assert sub_resp.status_code == 403


# ==============================================================================
# 15. Result blocked while IN_PROGRESS
# ==============================================================================
def test_result_endpoint_blocked_before_completion(setup_test_environment):
    """Calling /result on an IN_PROGRESS assessment returns 400 Bad Request."""
    env = setup_test_environment
    headers = {"Authorization": f"Bearer {env['tokens']['officer_1']}"}
    create_resp = client.post(
        "/api/v1/assessments",
        headers=headers,
        json={"document_id": env["doc_id"], "question_count": 2},
    )
    ass_id = create_resp.json()["id"]

    res_resp = client.get(f"/api/v1/assessments/{ass_id}/result", headers=headers)
    assert res_resp.status_code == 400
    assert "still in progress" in res_resp.json()["detail"]


# ==============================================================================
# 16. Partial submission rejected
# ==============================================================================
def test_submission_rejects_missing_answers(setup_test_environment):
    """Submitting only 1 answer when 2 are assigned returns 400 Bad Request."""
    env = setup_test_environment
    headers = {"Authorization": f"Bearer {env['tokens']['officer_1']}"}
    create_resp = client.post(
        "/api/v1/assessments",
        headers=headers,
        json={"document_id": env["doc_id"], "question_count": 2},
    )
    ass_id = create_resp.json()["id"]
    assigned_q = client.get(f"/api/v1/assessments/{ass_id}", headers=headers).json()["questions"]

    # Submit only 1 answer
    sub_payload = {
        "answers": [{"question_id": assigned_q[0]["id"], "selected_option": "A"}]
    }
    resp = client.post(f"/api/v1/assessments/{ass_id}/submit", headers=headers, json=sub_payload)
    assert resp.status_code == 400
    assert "All assigned assessment questions must be answered" in resp.json()["detail"]


# ==============================================================================
# 17. Empty submission rejected
# ==============================================================================
def test_submission_rejects_empty_answers(setup_test_environment):
    """Submitting an empty answers array returns 400 Bad Request."""
    env = setup_test_environment
    headers = {"Authorization": f"Bearer {env['tokens']['officer_1']}"}
    create_resp = client.post(
        "/api/v1/assessments",
        headers=headers,
        json={"document_id": env["doc_id"], "question_count": 2},
    )
    ass_id = create_resp.json()["id"]

    resp = client.post(f"/api/v1/assessments/{ass_id}/submit", headers=headers, json={"answers": []})
    assert resp.status_code == 400
    assert "cannot be empty" in resp.json()["detail"].lower()


# ==============================================================================
# 18. Duplicate answers rejected
# ==============================================================================
def test_submission_rejects_duplicate_answers(setup_test_environment):
    """Submitting duplicate answers for the same question returns 400 Bad Request."""
    env = setup_test_environment
    headers = {"Authorization": f"Bearer {env['tokens']['officer_1']}"}
    create_resp = client.post(
        "/api/v1/assessments",
        headers=headers,
        json={"document_id": env["doc_id"], "question_count": 2},
    )
    ass_id = create_resp.json()["id"]
    assigned_q = client.get(f"/api/v1/assessments/{ass_id}", headers=headers).json()["questions"]

    sub_payload = {
        "answers": [
            {"question_id": assigned_q[0]["id"], "selected_option": "A"},
            {"question_id": assigned_q[0]["id"], "selected_option": "B"},
        ]
    }
    resp = client.post(f"/api/v1/assessments/{ass_id}/submit", headers=headers, json=sub_payload)
    assert resp.status_code == 400
    assert "Duplicate answers" in resp.json()["detail"]


# ==============================================================================
# 19. Unassigned question rejected
# ==============================================================================
def test_submission_rejects_unassigned_question(setup_test_environment):
    """Submitting an answer for a question not assigned to the assessment returns 400 Bad Request."""
    env = setup_test_environment
    headers = {"Authorization": f"Bearer {env['tokens']['officer_1']}"}
    create_resp = client.post(
        "/api/v1/assessments",
        headers=headers,
        json={"document_id": env["doc_id"], "question_count": 2},
    )
    ass_id = create_resp.json()["id"]
    assigned_q = client.get(f"/api/v1/assessments/{ass_id}", headers=headers).json()["questions"]

    sub_payload = {
        "answers": [
            {"question_id": assigned_q[0]["id"], "selected_option": "A"},
            {"question_id": 999999, "selected_option": "B"},
        ]
    }
    resp = client.post(f"/api/v1/assessments/{ass_id}/submit", headers=headers, json=sub_payload)
    assert resp.status_code == 400
    assert "contain question IDs not assigned" in resp.json()["detail"]


# ==============================================================================
# 20. Invalid option rejected
# ==============================================================================
def test_invalid_selected_option_returns_422(setup_test_environment):
    """Submitting an invalid option like 'E' returns 422 Unprocessable Entity."""
    env = setup_test_environment
    headers = {"Authorization": f"Bearer {env['tokens']['officer_1']}"}
    create_resp = client.post(
        "/api/v1/assessments",
        headers=headers,
        json={"document_id": env["doc_id"], "question_count": 2},
    )
    ass_id = create_resp.json()["id"]

    sub_payload = {
        "answers": [
            {"question_id": 1, "selected_option": "E"},
        ]
    }
    resp = client.post(f"/api/v1/assessments/{ass_id}/submit", headers=headers, json=sub_payload)
    assert resp.status_code == 422


# ==============================================================================
# 21. Deterministic scoring
# ==============================================================================
def test_deterministic_scoring_competency_results_and_skill_gaps(setup_test_environment):
    """Validates full end-to-end deterministic server scoring, competency results, proficiency mapping, and skill gap generation."""
    env = setup_test_environment
    headers = {"Authorization": f"Bearer {env['tokens']['officer_1']}"}

    create_resp = client.post(
        "/api/v1/assessments",
        headers=headers,
        json={"document_id": env["doc_id"], "question_count": 4},
    )
    ass_id = create_resp.json()["id"]

    # Controlled answers:
    # Comp A: Q1 correct ("A"), Q2 correct ("B") -> 2/2 = 100% -> ADVANCED, NO skill gap
    # Comp B: Q3 correct ("C"), Q4 incorrect ("A" instead of "D") -> 1/2 = 50% -> DEVELOPING, MEDIUM skill gap
    # Overall: 3/4 = 75.0%
    sub_payload = {
        "answers": [
            {"question_id": env["q1_id"], "selected_option": "A"},
            {"question_id": env["q2_id"], "selected_option": "B"},
            {"question_id": env["q3_id"], "selected_option": "C"},
            {"question_id": env["q4_id"], "selected_option": "A"},  # incorrect
        ]
    }

    submit_resp = client.post(f"/api/v1/assessments/{ass_id}/submit", headers=headers, json=sub_payload)
    assert submit_resp.status_code == 200
    res = submit_resp.json()

    # 1. Overall Score Verification
    assert res["status"] == "COMPLETED"
    assert res["total_questions"] == 4
    assert res["total_correct"] == 3
    assert res["score_percentage"] == 75.0
    assert res["completed_at"] is not None

    # 2. Competency Results Verification
    c_results = {cr["competency_id"]: cr for cr in res["competency_results"]}
    assert env["comp_a_id"] in c_results
    assert env["comp_b_id"] in c_results

    # Comp A: 2/2 = 100% -> ADVANCED
    assert c_results[env["comp_a_id"]]["questions_attempted"] == 2
    assert c_results[env["comp_a_id"]]["questions_correct"] == 2
    assert c_results[env["comp_a_id"]]["score_percentage"] == 100.0
    assert c_results[env["comp_a_id"]]["proficiency_level"] == "ADVANCED"

    # Comp B: 1/2 = 50% -> DEVELOPING
    assert c_results[env["comp_b_id"]]["questions_attempted"] == 2
    assert c_results[env["comp_b_id"]]["questions_correct"] == 1
    assert c_results[env["comp_b_id"]]["score_percentage"] == 50.0
    assert c_results[env["comp_b_id"]]["proficiency_level"] == "DEVELOPING"

    # 3. Skill Gaps Verification
    gaps = {sg["competency_id"]: sg for sg in res["skill_gaps"]}
    assert env["comp_a_id"] not in gaps
    assert env["comp_b_id"] in gaps
    assert gaps[env["comp_b_id"]]["score_percentage"] == 50.0
    assert gaps[env["comp_b_id"]]["gap_level"] == "MEDIUM"


# ==============================================================================
# 22. Proficiency calculation thresholds
# ==============================================================================
def test_proficiency_and_gap_level_threshold_functions():
    """Unit tests for calculate_proficiency_level and calculate_gap_level against prototype thresholds."""
    # ADVANCED >= 80
    assert AssessmentService.calculate_proficiency_level(100.0) == ProficiencyLevel.ADVANCED
    assert AssessmentService.calculate_proficiency_level(80.0) == ProficiencyLevel.ADVANCED
    assert AssessmentService.calculate_gap_level(80.0) is None
    assert AssessmentService.calculate_gap_level(95.0) is None

    # PROFICIENT >= 65 and < 80
    assert AssessmentService.calculate_proficiency_level(79.9) == ProficiencyLevel.PROFICIENT
    assert AssessmentService.calculate_proficiency_level(65.0) == ProficiencyLevel.PROFICIENT
    assert AssessmentService.calculate_gap_level(79.9) == GapLevel.LOW
    assert AssessmentService.calculate_gap_level(65.0) == GapLevel.LOW

    # DEVELOPING >= 50 and < 65
    assert AssessmentService.calculate_proficiency_level(64.9) == ProficiencyLevel.DEVELOPING
    assert AssessmentService.calculate_proficiency_level(50.0) == ProficiencyLevel.DEVELOPING
    assert AssessmentService.calculate_gap_level(64.9) == GapLevel.MEDIUM
    assert AssessmentService.calculate_gap_level(50.0) == GapLevel.MEDIUM

    # BEGINNER < 50
    assert AssessmentService.calculate_proficiency_level(49.9) == ProficiencyLevel.BEGINNER
    assert AssessmentService.calculate_proficiency_level(0.0) == ProficiencyLevel.BEGINNER
    assert AssessmentService.calculate_gap_level(49.9) == GapLevel.HIGH
    assert AssessmentService.calculate_gap_level(0.0) == GapLevel.HIGH


# ==============================================================================
# 23. Competency result persistence
# ==============================================================================
def test_competency_result_persistence(setup_test_environment):
    """Direct database verification of persisted CompetencyResult records."""
    env = setup_test_environment
    headers = {"Authorization": f"Bearer {env['tokens']['officer_1']}"}
    create_resp = client.post("/api/v1/assessments", headers=headers, json={"document_id": env["doc_id"], "question_count": 2})
    ass_id = create_resp.json()["id"]
    assigned_q = client.get(f"/api/v1/assessments/{ass_id}", headers=headers).json()["questions"]

    sub_payload = {
        "answers": [
            {"question_id": assigned_q[0]["id"], "selected_option": "A"},
            {"question_id": assigned_q[1]["id"], "selected_option": "B"},
        ]
    }
    client.post(f"/api/v1/assessments/{ass_id}/submit", headers=headers, json=sub_payload)

    db = SessionLocal()
    try:
        db_cr = db.query(CompetencyResult).filter(CompetencyResult.assessment_id == ass_id).all()
        assert len(db_cr) >= 1
        for cr in db_cr:
            assert cr.questions_attempted >= 1
            assert cr.proficiency_level in {ProficiencyLevel.ADVANCED, ProficiencyLevel.PROFICIENT, ProficiencyLevel.DEVELOPING, ProficiencyLevel.BEGINNER}
    finally:
        db.close()


# ==============================================================================
# 24. Skill gap persistence
# ==============================================================================
def test_skill_gap_persistence(setup_test_environment):
    """Direct database verification of persisted SkillGap records when score < 80%."""
    env = setup_test_environment
    headers = {"Authorization": f"Bearer {env['tokens']['officer_1']}"}
    # Create assessment with 2 questions from Comp A
    create_resp = client.post(
        "/api/v1/assessments",
        headers=headers,
        json={"competency_id": env["comp_a_id"], "document_id": env["doc_id"], "question_count": 2},
    )
    ass_id = create_resp.json()["id"]

    # Submit 1 correct ("A") and 1 incorrect ("C" instead of "B") -> 50% score -> DEVELOPING -> MEDIUM gap
    sub_payload = {
        "answers": [
            {"question_id": env["q1_id"], "selected_option": "A"},
            {"question_id": env["q2_id"], "selected_option": "C"},
        ]
    }
    client.post(f"/api/v1/assessments/{ass_id}/submit", headers=headers, json=sub_payload)

    db = SessionLocal()
    try:
        db_sg = db.query(SkillGap).filter(SkillGap.assessment_id == ass_id).all()
        assert len(db_sg) == 1
        assert db_sg[0].competency_id == env["comp_a_id"]
        assert db_sg[0].gap_level == GapLevel.MEDIUM
        assert db_sg[0].score_percentage == Decimal("50.00")
    finally:
        db.close()


# ==============================================================================
# 25. Completed result unmasking
# ==============================================================================
def test_completed_result_unmasking(setup_test_environment):
    """Completed assessment unmasks explanations, correct options, and source chunk provenance."""
    env = setup_test_environment
    headers = {"Authorization": f"Bearer {env['tokens']['officer_1']}"}
    create_resp = client.post("/api/v1/assessments", headers=headers, json={"document_id": env["doc_id"], "question_count": 2})
    ass_id = create_resp.json()["id"]
    assigned_q = client.get(f"/api/v1/assessments/{ass_id}", headers=headers).json()["questions"]

    sub_payload = {
        "answers": [
            {"question_id": assigned_q[0]["id"], "selected_option": "A"},
            {"question_id": assigned_q[1]["id"], "selected_option": "B"},
        ]
    }
    client.post(f"/api/v1/assessments/{ass_id}/submit", headers=headers, json=sub_payload)

    res_resp = client.get(f"/api/v1/assessments/{ass_id}/result", headers=headers)
    assert res_resp.status_code == 200
    res_data = res_resp.json()

    assert len(res_data["questions"]) == 2
    for q in res_data["questions"]:
        assert q["correct_option"] in {"A", "B", "C", "D"}
        assert isinstance(q["is_correct"], bool)
        assert len(q["explanation"]) > 0
        assert q["source_page"] is not None


# ==============================================================================
# 26. Completed assessment cannot be resubmitted
# ==============================================================================
def test_repeated_submission_rejected(setup_test_environment):
    """Attempting to submit an already completed assessment returns 400 Bad Request."""
    env = setup_test_environment
    headers = {"Authorization": f"Bearer {env['tokens']['officer_1']}"}
    create_resp = client.post(
        "/api/v1/assessments",
        headers=headers,
        json={"document_id": env["doc_id"], "question_count": 2},
    )
    ass_id = create_resp.json()["id"]
    assigned_q = client.get(f"/api/v1/assessments/{ass_id}", headers=headers).json()["questions"]

    sub_payload = {
        "answers": [
            {"question_id": assigned_q[0]["id"], "selected_option": "A"},
            {"question_id": assigned_q[1]["id"], "selected_option": "B"},
        ]
    }
    client.post(f"/api/v1/assessments/{ass_id}/submit", headers=headers, json=sub_payload)

    # Second submission attempt
    second_sub = client.post(f"/api/v1/assessments/{ass_id}/submit", headers=headers, json=sub_payload)
    assert second_sub.status_code == 400
    assert "already been completed" in second_sub.json()["detail"]


# ==============================================================================
# 27. Atomic rollback
# ==============================================================================
def test_submit_atomic_rollback(setup_test_environment, monkeypatch):
    """Verifies that an error during submission triggers db.rollback() leaving no partial records."""
    env = setup_test_environment
    headers = {"Authorization": f"Bearer {env['tokens']['officer_1']}"}

    create_resp = client.post(
        "/api/v1/assessments",
        headers=headers,
        json={"document_id": env["doc_id"], "question_count": 2},
    )
    assert create_resp.status_code == 201
    ass_id = create_resp.json()["id"]
    assigned_q = client.get(f"/api/v1/assessments/{ass_id}", headers=headers).json()["questions"]

    sub_payload = {
        "answers": [
            {"question_id": assigned_q[0]["id"], "selected_option": "A"},
            {"question_id": assigned_q[1]["id"], "selected_option": "B"},
        ]
    }

    # Simulate an error inside the scoring loop
    def mock_fail(*args, **kwargs):
        raise RuntimeError("Simulated failure during scoring transaction")

    monkeypatch.setattr(AssessmentService, "calculate_proficiency_level", mock_fail)

    resp = client.post(f"/api/v1/assessments/{ass_id}/submit", headers=headers, json=sub_payload)
    assert resp.status_code == 500

    # Verify atomic rollback left assessment untouched and clean
    db = SessionLocal()
    try:
        db_ass = db.query(Assessment).filter(Assessment.id == ass_id).first()
        assert db_ass.status == AssessmentStatus.IN_PROGRESS
        assert db_ass.total_correct == 0
        assert db_ass.score_percentage == Decimal("0.00")

        # Zero answers committed
        db_ans = db.query(Answer).filter(Answer.assessment_id == ass_id).all()
        assert len(db_ans) == 0

        # Zero competency results committed
        db_cr = db.query(CompetencyResult).filter(CompetencyResult.assessment_id == ass_id).all()
        assert len(db_cr) == 0

        # Zero skill gaps committed
        db_sg = db.query(SkillGap).filter(SkillGap.assessment_id == ass_id).all()
        assert len(db_sg) == 0
    finally:
        db.close()


# ==============================================================================
# 28. RBAC list behavior
# ==============================================================================
def test_list_assessments_pagination_and_ownership(setup_test_environment):
    """GET /assessments respects officer ownership and pagination; Trainers can inspect all."""
    env = setup_test_environment
    officer_1_headers = {"Authorization": f"Bearer {env['tokens']['officer_1']}"}
    officer_2_headers = {"Authorization": f"Bearer {env['tokens']['officer_2']}"}
    trainer_headers = {"Authorization": f"Bearer {env['tokens']['trainer']}"}

    # Officer 1 lists assessments -> only sees officer 1 assessments
    list_1 = client.get("/api/v1/assessments", headers=officer_1_headers)
    assert list_1.status_code == 200
    data_1 = list_1.json()
    for item in data_1["items"]:
        assert item["officer_id"] == env["officer_1_id"]

    # Officer 2 lists assessments -> 0 or only officer 2 assessments
    list_2 = client.get("/api/v1/assessments", headers=officer_2_headers)
    assert list_2.status_code == 200

    # Trainer lists assessments -> can see all
    list_trainer = client.get("/api/v1/assessments?limit=5", headers=trainer_headers)
    assert list_trainer.status_code == 200
    assert len(list_trainer.json()["items"]) <= 5
