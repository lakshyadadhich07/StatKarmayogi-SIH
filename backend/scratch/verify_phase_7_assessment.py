from datetime import datetime
from decimal import Decimal
import os
import sys
import uuid
from fastapi.testclient import TestClient
from sqlalchemy import inspect

# Ensure backend root is on PYTHONPATH
sys.path.insert(0, r"c:\SIH\backend")

from app.core.config import settings
from app.core.security import create_access_token
from app.db.seed import seed_roles
from app.db.session import SessionLocal, engine
from app.main import app
from app.models.answer import Answer
from app.models.assessment import Assessment
from app.models.assessment_question import AssessmentQuestion
from app.models.competency import Competency
from app.models.competency_result import CompetencyResult
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.enums import AssessmentStatus, DocumentStatus, GapLevel, ProficiencyLevel, QuestionDifficulty, QuestionStatus, RoleName
from app.models.question import Question
from app.models.role import Role
from app.models.skill_gap import SkillGap
from app.models.user import User


def run_verification():
    print("=" * 80)
    print("STATKARMAYOGI PHASE 7 LIVE VERIFICATION — ASSESSMENT, SCORING & SKILL GAPS")
    print("=" * 80)

    client = TestClient(app)
    db = SessionLocal()

    try:
        # 1. Seed roles
        seed_roles(db)
        officer_role = db.query(Role).filter_by(name=RoleName.OFFICER.value).first()
        trainer_role = db.query(Role).filter_by(name=RoleName.TRAINER.value).first()
        sme_role = db.query(Role).filter_by(name=RoleName.SME.value).first()
        admin_role = db.query(Role).filter_by(name=RoleName.ADMIN.value).first()

        suffix = uuid.uuid4().hex[:6]

        # 2. Create Users
        officer_1 = User(
            name="Statistical Officer Delhi",
            email=f"officer1_live_{suffix}@mospi.gov.in",
            password_hash="test_hash",
            role_id=officer_role.id,
            department="Field Operations Division",
            is_active=True,
        )
        officer_2 = User(
            name="Statistical Officer Mumbai",
            email=f"officer2_live_{suffix}@mospi.gov.in",
            password_hash="test_hash",
            role_id=officer_role.id,
            department="National Accounts Division",
            is_active=True,
        )
        trainer = User(
            name="NSSTA Training Director",
            email=f"trainer_live_{suffix}@mospi.gov.in",
            password_hash="test_hash",
            role_id=trainer_role.id,
            department="Training Academy Greater Noida",
            is_active=True,
        )
        sme = User(
            name="Senior SME Evaluator",
            email=f"sme_live_{suffix}@mospi.gov.in",
            password_hash="test_hash",
            role_id=sme_role.id,
            department="Economic Statistics Wing",
            is_active=True,
        )
        admin = User(
            name="MoSPI Admin",
            email=f"admin_live_{suffix}@mospi.gov.in",
            password_hash="test_hash",
            role_id=admin_role.id,
            department="Computer Centre New Delhi",
            is_active=True,
        )
        db.add_all([officer_1, officer_2, trainer, sme, admin])
        db.commit()

        # Auth tokens
        t_off1 = create_access_token({"sub": str(officer_1.id), "email": officer_1.email, "role": RoleName.OFFICER.value})
        t_off2 = create_access_token({"sub": str(officer_2.id), "email": officer_2.email, "role": RoleName.OFFICER.value})
        t_trainer = create_access_token({"sub": str(trainer.id), "email": trainer.email, "role": RoleName.TRAINER.value})
        t_sme = create_access_token({"sub": str(sme.id), "email": sme.email, "role": RoleName.SME.value})
        t_admin = create_access_token({"sub": str(admin.id), "email": admin.email, "role": RoleName.ADMIN.value})

        h_off1 = {"Authorization": f"Bearer {t_off1}"}
        h_off2 = {"Authorization": f"Bearer {t_off2}"}
        h_trainer = {"Authorization": f"Bearer {t_trainer}"}
        h_sme = {"Authorization": f"Bearer {t_sme}"}
        h_admin = {"Authorization": f"Bearer {t_admin}"}

        print("[OK] Step 1: Seeded roles and authenticated test personas (Officer 1, Officer 2, Trainer, SME, Admin).")

        # 3. Create Competencies
        comp_asi = Competency(
            code=f"ASI_EST_{suffix.upper()}",
            name="ASI Survey Methodology & GVA Calculation",
            description="Competency in sampling, frame definitions, and output value computation.",
            category="MoSPI Survey Statistics",
            is_active=True,
        )
        comp_iip = Competency(
            code=f"IIP_IND_{suffix.upper()}",
            name="Index of Industrial Production (IIP)",
            description="Compilation of monthly production indices and Laspeyres formula weighting.",
            category="MoSPI Macroeconomic Indicators",
            is_active=True,
        )
        db.add_all([comp_asi, comp_iip])
        db.commit()
        print(f"[OK] Step 2: Created competencies: '{comp_asi.name}' and '{comp_iip.name}'.")

        # 4. Create Document, Chunks and Questions
        doc = Document(
            uploaded_by=trainer.id,
            filename=f"mospi_statistical_standards_{suffix}.pdf",
            file_type="pdf",
            file_path=f"storage/documents/standards_{suffix}.pdf",
            status=DocumentStatus.PROCESSED,
        )
        db.add(doc)
        db.commit()

        c1 = DocumentChunk(document_id=doc.id, chunk_index=0, page_number=12, content_hash=f"hash1_{suffix}", chroma_id=f"chr1_{suffix}")
        c2 = DocumentChunk(document_id=doc.id, chunk_index=1, page_number=15, content_hash=f"hash2_{suffix}", chroma_id=f"chr2_{suffix}")
        c3 = DocumentChunk(document_id=doc.id, chunk_index=2, page_number=45, content_hash=f"hash3_{suffix}", chroma_id=f"chr3_{suffix}")
        c4 = DocumentChunk(document_id=doc.id, chunk_index=3, page_number=48, content_hash=f"hash4_{suffix}", chroma_id=f"chr4_{suffix}")
        db.add_all([c1, c2, c3, c4])
        db.commit()

        # Questions for Comp ASI (APPROVED)
        q1 = Question(
            document_id=doc.id,
            competency_id=comp_asi.id,
            question_text="What comprises Gross Output in Annual Survey of Industries?",
            option_a="Ex-factory value of products manufactured plus industrial services rendered",
            option_b="Only net excise duties collected",
            option_c="Gross capital formation excluding inventories",
            option_d="Subsidies received on production",
            correct_option="A",
            difficulty=QuestionDifficulty.MEDIUM,
            explanation="ASI methodology defines gross output as total ex-factory value of goods produced and industrial services.",
            source_page=12,
            source_chunk_id=c1.id,
            generation_model="mistral-large-latest",
            status=QuestionStatus.APPROVED,
            created_by=trainer.id,
        )
        q2 = Question(
            document_id=doc.id,
            competency_id=comp_asi.id,
            question_text="Which factories constitute the census sector in ASI?",
            option_a="All factories employing 100 or more workers",
            option_b="Factories employing 5 or fewer workers",
            option_c="Factories outside India",
            option_d="Unregistered household units",
            correct_option="A",
            difficulty=QuestionDifficulty.EASY,
            explanation="Factories employing 100+ workers are surveyed on a complete enumeration census basis.",
            source_page=15,
            source_chunk_id=c2.id,
            generation_model="mistral-large-latest",
            status=QuestionStatus.APPROVED,
            created_by=trainer.id,
        )

        # Questions for Comp IIP (APPROVED)
        q3 = Question(
            document_id=doc.id,
            competency_id=comp_iip.id,
            question_text="Which weighting formula is utilized in compiling the IIP?",
            option_a="Paasche index formula",
            option_b="Laspeyres weighted arithmetic mean formula",
            option_c="Fisher ideal index",
            option_d="Simple geometric mean",
            correct_option="B",
            difficulty=QuestionDifficulty.MEDIUM,
            explanation="IIP uses the Laspeyres base-weighted formula according to MoSPI standards.",
            source_page=45,
            source_chunk_id=c3.id,
            generation_model="mistral-large-latest",
            status=QuestionStatus.APPROVED,
            created_by=trainer.id,
        )
        q4 = Question(
            document_id=doc.id,
            competency_id=comp_iip.id,
            question_text="What is the current base year for the all-India IIP series?",
            option_a="1993-94",
            option_b="2004-05",
            option_c="2011-12",
            option_d="2020-21",
            correct_option="C",
            difficulty=QuestionDifficulty.EASY,
            explanation="The current base year for all-India IIP is 2011-12.",
            source_page=48,
            source_chunk_id=c4.id,
            generation_model="mistral-large-latest",
            status=QuestionStatus.APPROVED,
            created_by=trainer.id,
        )

        # Questions that MUST be excluded:
        q_pending = Question(
            document_id=doc.id,
            competency_id=comp_asi.id,
            question_text="Pending question text?",
            option_a="A", option_b="B", option_c="C", option_d="D",
            correct_option="A", difficulty=QuestionDifficulty.EASY,
            status=QuestionStatus.PENDING_REVIEW, created_by=trainer.id,
        )
        q_rejected = Question(
            document_id=doc.id,
            competency_id=comp_iip.id,
            question_text="Rejected question text?",
            option_a="A", option_b="B", option_c="C", option_d="D",
            correct_option="A", difficulty=QuestionDifficulty.EASY,
            status=QuestionStatus.REJECTED, created_by=trainer.id,
        )
        q_null_comp = Question(
            document_id=doc.id,
            competency_id=None,
            question_text="General question without competency tag?",
            option_a="A", option_b="B", option_c="C", option_d="D",
            correct_option="A", difficulty=QuestionDifficulty.EASY,
            status=QuestionStatus.APPROVED, created_by=trainer.id,
        )
        db.add_all([q1, q2, q3, q4, q_pending, q_rejected, q_null_comp])
        db.commit()

        print("[OK] Step 3: Created 4 APPROVED competency-tagged questions, plus 1 pending, 1 rejected, and 1 null-competency question.")

        # 5. Officer 1 Creates Diagnostic Assessment
        create_resp = client.post(
            "/api/v1/assessments",
            headers=h_off1,
            json={"title": "ASI & IIP Competency Assessment", "document_id": doc.id, "question_count": 4},
        )
        assert create_resp.status_code == 201, f"Failed to create assessment: {create_resp.text}"
        ass_data = create_resp.json()
        ass_id = ass_data["id"]
        assert ass_data["status"] == "IN_PROGRESS"
        assert ass_data["total_questions"] == 4
        print(f"[OK] Step 4: Officer 1 created assessment (ID={ass_id}, status=IN_PROGRESS).")

        # 6. Retrieve Assessment and Verify Question Ordering & Answer Masking
        detail_resp = client.get(f"/api/v1/assessments/{ass_id}", headers=h_off1)
        assert detail_resp.status_code == 200
        detail_data = detail_resp.json()
        questions = detail_data["questions"]
        assert len(questions) == 4

        # Deterministic ordering check (questions.id ASC)
        q_ids = [q["id"] for q in questions]
        assert q_ids == sorted(q_ids), "Questions are not deterministically ordered by ID ASC"
        assert set(q_ids) == {q1.id, q2.id, q3.id, q4.id}
        assert q_pending.id not in q_ids
        assert q_rejected.id not in q_ids
        assert q_null_comp.id not in q_ids
        print(f"[OK] Step 5: Deterministic question ordering verified (IDs: {q_ids}).")

        # Strict Security / Answer Key Masking Check
        for q in questions:
            assert "correct_option" not in q, "LEAK: correct_option exposed in active assessment!"
            assert "is_correct" not in q, "LEAK: is_correct exposed in active assessment!"
            assert "explanation" not in q, "LEAK: explanation exposed in active assessment!"
            assert "source_page" not in q, "LEAK: source_page exposed in active assessment!"
            assert "source_chunk_id" not in q, "LEAK: source_chunk_id exposed in active assessment!"
        print("[OK] Step 6: Security verified — answer keys, explanations, and citations are strictly masked.")

        # 7. Check /result endpoint is blocked while IN_PROGRESS
        blocked_res = client.get(f"/api/v1/assessments/{ass_id}/result", headers=h_off1)
        assert blocked_res.status_code == 400
        print("[OK] Step 7: Access to results is properly blocked while assessment is IN_PROGRESS (400).")

        # 8. Check RBAC on creation: Trainer and SME must receive 403 Forbidden
        trainer_create = client.post("/api/v1/assessments", headers=h_trainer, json={"question_count": 2})
        assert trainer_create.status_code == 403, f"Expected 403 for trainer create, got {trainer_create.status_code}"
        sme_create = client.post("/api/v1/assessments", headers=h_sme, json={"question_count": 2})
        assert sme_create.status_code == 403, f"Expected 403 for SME create, got {sme_create.status_code}"
        print("[OK] Step 8: RBAC verified — Trainer and SME creation attempts rejected (403).")

        # 9. Check empty submission rejection (400)
        empty_sub = client.post(f"/api/v1/assessments/{ass_id}/submit", headers=h_off1, json={"answers": []})
        assert empty_sub.status_code == 400
        print("[OK] Step 9: Empty submission correctly rejected (400).")

        # 10. Check partial submission rejection (All questions must be answered)
        partial_sub = client.post(
            f"/api/v1/assessments/{ass_id}/submit",
            headers=h_off1,
            json={"answers": [{"question_id": q_ids[0], "selected_option": "A"}]},
        )
        assert partial_sub.status_code == 400
        assert "All assigned assessment questions must be answered" in partial_sub.json()["detail"]
        print("[OK] Step 10: Partial submission correctly rejected (400) — all questions must be answered.")

        # 11. Check duplicate answers rejection (400)
        dup_sub_attempt = client.post(
            f"/api/v1/assessments/{ass_id}/submit",
            headers=h_off1,
            json={"answers": [
                {"question_id": q_ids[0], "selected_option": "A"},
                {"question_id": q_ids[0], "selected_option": "B"},
            ]},
        )
        assert dup_sub_attempt.status_code == 400
        print("[OK] Step 11: Duplicate question submission correctly rejected (400).")

        # 12. Check unassigned question rejection (400)
        unassigned_sub = client.post(
            f"/api/v1/assessments/{ass_id}/submit",
            headers=h_off1,
            json={"answers": [
                {"question_id": q_ids[0], "selected_option": "A"},
                {"question_id": 999999, "selected_option": "B"},
            ]},
        )
        assert unassigned_sub.status_code == 400
        print("[OK] Step 12: Unassigned question submission correctly rejected (400).")

        # 13. Officer 1 Submits Controlled Answers
        # Target evaluation:
        # Comp ASI (q1, q2): q1="A" (correct), q2="A" (correct) -> 2/2 = 100% -> ADVANCED -> 0 skill gaps
        # Comp IIP (q3, q4): q3="B" (correct), q4="A" (incorrect, correct is "C") -> 1/2 = 50% -> DEVELOPING -> MEDIUM gap
        # Overall score: 3/4 = 75.0%
        sub_payload = {
            "answers": [
                {"question_id": q1.id, "selected_option": "A"},
                {"question_id": q2.id, "selected_option": "A"},
                {"question_id": q3.id, "selected_option": "B"},
                {"question_id": q4.id, "selected_option": "A"},  # incorrect
            ]
        }
        submit_resp = client.post(f"/api/v1/assessments/{ass_id}/submit", headers=h_off1, json=sub_payload)
        assert submit_resp.status_code == 200, f"Submit failed: {submit_resp.text}"
        res_data = submit_resp.json()

        # 10. Verify Overall Score & Status Transition
        assert res_data["status"] == "COMPLETED"
        assert res_data["total_questions"] == 4
        assert res_data["total_correct"] == 3
        assert res_data["score_percentage"] == 75.0
        assert res_data["completed_at"] is not None
        print(f"[OK] Step 9: Overall score calculated deterministically: 3/4 correct = 75.0%, status=COMPLETED.")

        # 11. Verify Competency-Level Results
        c_results = {cr["competency_id"]: cr for cr in res_data["competency_results"]}
        assert comp_asi.id in c_results
        assert comp_iip.id in c_results

        asi_res = c_results[comp_asi.id]
        assert asi_res["questions_attempted"] == 2
        assert asi_res["questions_correct"] == 2
        assert asi_res["score_percentage"] == 100.0
        assert asi_res["proficiency_level"] == "ADVANCED"
        print(f"[OK] Step 10: Competency ASI scored 100% -> Proficiency: ADVANCED.")

        iip_res = c_results[comp_iip.id]
        assert iip_res["questions_attempted"] == 2
        assert iip_res["questions_correct"] == 1
        assert iip_res["score_percentage"] == 50.0
        assert iip_res["proficiency_level"] == "DEVELOPING"
        print(f"[OK] Step 11: Competency IIP scored 50% -> Proficiency: DEVELOPING.")

        # 12. Verify Skill Gap Identification
        gaps = {sg["competency_id"]: sg for sg in res_data["skill_gaps"]}
        assert comp_asi.id not in gaps, "Comp ASI (100%) should have NO skill gap!"
        assert comp_iip.id in gaps, "Comp IIP (50%) should have an identified skill gap!"
        assert gaps[comp_iip.id]["gap_level"] == "MEDIUM"
        assert gaps[comp_iip.id]["score_percentage"] == 50.0
        print(f"[OK] Step 12: Skill gap verified: Competency IIP identified as GapLevel.MEDIUM (50%).")

        # 13. Verify Results Endpoint Unmasks Educational Explanations
        result_resp = client.get(f"/api/v1/assessments/{ass_id}/result", headers=h_off1)
        assert result_resp.status_code == 200
        r_data = result_resp.json()
        assert len(r_data["questions"]) == 4
        for q in r_data["questions"]:
            assert q["correct_option"] in {"A", "B", "C", "D"}
            assert isinstance(q["is_correct"], bool)
            assert len(q["explanation"]) > 0
            assert q["source_page"] is not None
        print("[OK] Step 13: Detailed post-assessment question review unmasked with explanations and source pages.")

        # 14. Verify Resubmission is Blocked
        dup_sub = client.post(f"/api/v1/assessments/{ass_id}/submit", headers=h_off1, json=sub_payload)
        assert dup_sub.status_code == 400
        print("[OK] Step 14: Repeated submission of completed assessment correctly rejected (400).")

        # 15. Verify RBAC / Officer Data Isolation
        off2_attempt = client.get(f"/api/v1/assessments/{ass_id}", headers=h_off2)
        assert off2_attempt.status_code == 403
        off2_sub = client.post(f"/api/v1/assessments/{ass_id}/submit", headers=h_off2, json=sub_payload)
        assert off2_sub.status_code == 403
        print("[OK] Step 15: Officer data isolation enforced — Officer 2 access to Officer 1's assessment rejected (403).")

        # 16. Verify Trainer & Admin Oversight
        t_res = client.get(f"/api/v1/assessments/{ass_id}/result", headers=h_trainer)
        assert t_res.status_code == 200
        a_res = client.get(f"/api/v1/assessments/{ass_id}/result", headers=h_admin)
        assert a_res.status_code == 200
        print("[OK] Step 16: Trainer and Admin can inspect completed assessment results.")

        # 17. Direct Database Inspection (PostgreSQL)
        db.expire_all()
        db_ass = db.query(Assessment).filter(Assessment.id == ass_id).first()
        assert db_ass.status == AssessmentStatus.COMPLETED
        assert db_ass.score_percentage == Decimal("75.00")
        assert db_ass.total_correct == 3

        db_ans = db.query(Answer).filter(Answer.assessment_id == ass_id).all()
        assert len(db_ans) == 4

        db_cr = db.query(CompetencyResult).filter(CompetencyResult.assessment_id == ass_id).all()
        assert len(db_cr) == 2

        db_sg = db.query(SkillGap).filter(SkillGap.assessment_id == ass_id).all()
        assert len(db_sg) == 1
        assert db_sg[0].gap_level == GapLevel.MEDIUM
        print("[OK] Step 17: Database records directly verified in PostgreSQL (answers, competency_results, skill_gaps).")

        # 18. Schema Integrity Check: Confirm ZERO schema changes occurred
        insp = inspect(engine)
        all_tables = insp.get_table_names()
        assert len(all_tables) == 16, f"Expected 16 tables, found {len(all_tables)}"
        assert "assessments" in all_tables
        assert "assessment_questions" in all_tables
        assert "answers" in all_tables
        assert "competency_results" in all_tables
        assert "skill_gaps" in all_tables
        print("[OK] Step 18: ZERO schema changes confirmed — exactly 16 existing tables present.")

        print("\n" + "=" * 80)
        print("ALL 18 PHASE 7 LIVE VERIFICATION STEPS PASSED FLAWLESSLY!")
        print("=" * 80)

    finally:
        db.close()


if __name__ == "__main__":
    run_verification()
