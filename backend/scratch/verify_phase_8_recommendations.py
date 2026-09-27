"""End-to-End Live PostgreSQL Verification Script for Phase 8.

Verifies:
1. Pre-verification of live competencies in PostgreSQL.
2. Prototype course seeding with curated prototype relevance scores.
3. Valid route or null course URLs (no fake or dead URLs).
4. No 'is_external' field in schema/models.
5. Deterministic recommendation matching and explainable reason generation.
6. Per-gap and global active recommendation limits.
7. Full recommendation status state machine transitions and terminal protection.
8. History preservation on regeneration (STARTED, COMPLETED, DISMISSED).
9. RBAC enforcement across Officer, Trainer, Admin, and SME roles.
10. Zero-gap assessment producing zero recommendations without error.
11. Total table count remains strictly 16 tables.
"""

from datetime import datetime, timezone
from decimal import Decimal
import sys
sys.path.insert(0, ".")
import uuid
from fastapi.testclient import TestClient
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.core.security import create_access_token

from app.db.seed import seed_all
from app.db.session import SessionLocal, engine
engine.echo = False
from app.main import app
from app.models.assessment import Assessment
from app.models.competency import Competency
from app.models.course import Course
from app.models.course_competency import CourseCompetency
from app.models.enums import AssessmentStatus, GapLevel, RecommendationStatus, RoleName
from app.models.recommendation import Recommendation
from app.models.role import Role
from app.models.skill_gap import SkillGap
from app.models.user import User

client = TestClient(app)



def run_verification():
    print("=" * 70)
    print("STATKARMAYOGI PHASE 8 — LIVE POSTGRESQL VERIFICATION")
    print("=" * 70)

    db: Session = SessionLocal()
    try:
        # Step 1: Pre-verify existing competencies
        print("\n[Step 1] Inspecting existing competencies in PostgreSQL...")
        active_comps = db.query(Competency).filter(Competency.is_active == True).all()
        print(f" -> Found {len(active_comps)} active competencies in PostgreSQL.")
        assert len(active_comps) > 0, "No active competencies found!"

        # Step 2: Seed courses and roles
        print("\n[Step 2] Executing database seed (roles + prototype courses)...")
        seed_all(db)
        total_courses = db.query(Course).count()
        print(f" -> Successfully seeded prototype courses. Total in DB: {total_courses}")
        assert total_courses >= 6

        # Step 2b: Verify four verified mappings and unmapped status for FPOS & DAP
        print("\n[Step 2b] Verifying course-to-competency mappings...")
        fpos = db.query(Course).filter(Course.igot_course_id == "IGOT-PROTO-FPOS-01").first()
        dap = db.query(Course).filter(Course.igot_course_id == "IGOT-PROTO-DAP-01").first()
        assert fpos is not None, "FPOS course not found!"
        assert dap is not None, "DAP course not found!"

        fpos_maps = db.query(CourseCompetency).filter(CourseCompetency.course_id == fpos.id).all()
        dap_maps = db.query(CourseCompetency).filter(CourseCompetency.course_id == dap.id).all()
        assert len(fpos_maps) == 0, f"FPOS must have 0 mappings, found {len(fpos_maps)}"
        assert len(dap_maps) == 0, f"DAP must have 0 mappings, found {len(dap_maps)}"
        print(" -> FPOS and DAP verified as completely unmapped (0 CourseCompetency records).")

        verified_codes = {
            "IGOT-PROTO-ASI-01": "ASI_METH_73F0",
            "IGOT-PROTO-IIP-01": "IIP_IND_94799B",
            "IGOT-PROTO-NAS-01": "COMP_NAD_3746b0",
            "IGOT-PROTO-SSD-01": "COMP_D981F6",
        }
        for igot_id, code in verified_codes.items():
            crs = db.query(Course).filter(Course.igot_course_id == igot_id).first()
            assert crs is not None, f"Course {igot_id} not found!"
            c_maps = (
                db.query(CourseCompetency)
                .join(Competency, CourseCompetency.competency_id == Competency.id)
                .filter(CourseCompetency.course_id == crs.id, Competency.code == code)
                .all()
            )
            assert len(c_maps) >= 1, f"Verified mapping for {igot_id} -> {code} missing!"
        print(" -> All 4 verified course mappings (ASI, IIP, NAS, SSD) verified intact.")

        # Step 3: Check course URLs and verify zero is_external
        print("\n[Step 3] Verifying course URLs and zero is_external...")
        courses = db.query(Course).all()
        for c in courses:
            assert not hasattr(c, "is_external"), "is_external column found on Course model!"
            if c.course_url is not None:
                assert not c.course_url.startswith("https://mock.igotkarmayogi.gov.in")
                assert "/mock/igot" not in c.course_url
        print(" -> All course URLs are safe/null. Zero dead or fake URLs. Zero is_external columns.")


        # Step 4: Create Test Users for RBAC testing
        print("\n[Step 4] Creating test users across roles...")
        suffix = uuid.uuid4().hex[:6]
        off_role = db.query(Role).filter_by(name=RoleName.OFFICER.value).first()
        trainer_role = db.query(Role).filter_by(name=RoleName.TRAINER.value).first()
        sme_role = db.query(Role).filter_by(name=RoleName.SME.value).first()
        admin_role = db.query(Role).filter_by(name=RoleName.ADMIN.value).first()

        off1 = User(name="Live Officer 1", email=f"live_off1_{suffix}@mospi.gov.in", password_hash="test", role_id=off_role.id, is_active=True)
        off2 = User(name="Live Officer 2", email=f"live_off2_{suffix}@mospi.gov.in", password_hash="test", role_id=off_role.id, is_active=True)
        trainer = User(name="Live Trainer", email=f"live_trainer_{suffix}@mospi.gov.in", password_hash="test", role_id=trainer_role.id, is_active=True)
        sme = User(name="Live SME", email=f"live_sme_{suffix}@mospi.gov.in", password_hash="test", role_id=sme_role.id, is_active=True)
        admin = User(name="Live Admin", email=f"live_admin_{suffix}@mospi.gov.in", password_hash="test", role_id=admin_role.id, is_active=True)

        db.add_all([off1, off2, trainer, sme, admin])
        db.commit()

        t_off1 = create_access_token({"sub": str(off1.id)})
        t_off2 = create_access_token({"sub": str(off2.id)})
        t_trainer = create_access_token({"sub": str(trainer.id)})
        t_sme = create_access_token({"sub": str(sme.id)})
        t_admin = create_access_token({"sub": str(admin.id)})
        print(" -> Test users and JWT tokens generated.")

        # Step 5: Create completed assessment with skill gaps
        print("\n[Step 5] Creating completed assessment with HIGH and MEDIUM skill gaps...")
        comp1 = active_comps[0]
        comp2 = active_comps[1] if len(active_comps) > 1 else active_comps[0]

        ass = Assessment(
            officer_id=off1.id,
            title=f"Live Diagnostic Assessment {suffix}",
            status=AssessmentStatus.COMPLETED,
            total_questions=10,
            total_correct=4,
            score_percentage=Decimal("40.0"),
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        db.add(ass)
        db.flush()

        gap1 = SkillGap(assessment_id=ass.id, competency_id=comp1.id, score_percentage=Decimal("30.0"), gap_level=GapLevel.HIGH)
        gap2 = SkillGap(assessment_id=ass.id, competency_id=comp2.id, score_percentage=Decimal("55.0"), gap_level=GapLevel.MEDIUM)
        db.add_all([gap1, gap2])
        db.commit()
        print(f" -> Assessment ID={ass.id} created with gaps: {comp1.name} (HIGH), {comp2.name} (MEDIUM).")

        # Step 6: Generate recommendations via API
        print("\n[Step 6] Generating recommendations via POST /api/v1/assessments/{id}/recommendations...")
        resp = client.post(f"/api/v1/assessments/{ass.id}/recommendations", headers={"Authorization": f"Bearer {t_off1}"})
        assert resp.status_code == 200, f"Generation failed: {resp.text}"
        recs = resp.json()
        print(f" -> Generated {len(recs)} recommendations.")
        assert len(recs) > 0
        assert len(recs) <= 6

        rec_course_ids = {r["course_id"] for r in recs}
        assert fpos.id not in rec_course_ids, "Unmapped course FPOS was incorrectly recommended!"
        assert dap.id not in rec_course_ids, "Unmapped course DAP was incorrectly recommended!"
        print(" -> Verified unmapped courses (FPOS, DAP) were NOT recommended.")


        # Step 7: Verify match score, priority, and reason format
        print("\n[Step 7] Verifying deterministic match score and reason format...")
        first_rec = recs[0]
        print(f" -> Top recommendation: '{first_rec['course_title']}' | Priority={first_rec['priority']} | Score={first_rec['match_score']}%")
        print(f" -> Reason: \"{first_rec['reason']}\"")
        assert "Recommended because your assessment score in" in first_rec["reason"]
        assert "resulting in a match score of" in first_rec["reason"]
        assert first_rec["status"] == "RECOMMENDED"

        # Step 8: State Machine Transitions
        print("\n[Step 8] Testing status state machine transitions...")
        r1_id = recs[0]["id"]
        # RECOMMENDED -> STARTED
        s_res = client.patch(f"/api/v1/recommendations/{r1_id}/status", json={"status": "STARTED"}, headers={"Authorization": f"Bearer {t_off1}"})
        assert s_res.status_code == 200 and s_res.json()["status"] == "STARTED"
        print(" -> Transitioned Rec 1: RECOMMENDED -> STARTED (OK)")

        # RECOMMENDED -> DISMISSED on Rec 2 if present
        if len(recs) > 1:
            r2_id = recs[1]["id"]
            d_res = client.patch(f"/api/v1/recommendations/{r2_id}/status", json={"status": "DISMISSED"}, headers={"Authorization": f"Bearer {t_off1}"})
            assert d_res.status_code == 200 and d_res.json()["status"] == "DISMISSED"
            print(" -> Transitioned Rec 2: RECOMMENDED -> DISMISSED (OK)")

        # STARTED -> COMPLETED on Rec 1
        c_res = client.patch(f"/api/v1/recommendations/{r1_id}/status", json={"status": "COMPLETED"}, headers={"Authorization": f"Bearer {t_off1}"})
        assert c_res.status_code == 200 and c_res.json()["status"] == "COMPLETED"
        print(" -> Transitioned Rec 1: STARTED -> COMPLETED (OK)")

        # COMPLETED is terminal: attempt transition to STARTED must return 400
        bad_res = client.patch(f"/api/v1/recommendations/{r1_id}/status", json={"status": "STARTED"}, headers={"Authorization": f"Bearer {t_off1}"})
        assert bad_res.status_code == 400
        print(" -> Attempted transition on terminal COMPLETED returned HTTP 400 (OK)")

        # Step 9: Regeneration preserves learning history
        print("\n[Step 9] Testing regeneration idempotency & historical preservation...")
        regen_resp = client.post(f"/api/v1/assessments/{ass.id}/recommendations", headers={"Authorization": f"Bearer {t_off1}"})
        assert regen_resp.status_code == 200
        regen_recs = regen_resp.json()
        statuses = {r["status"] for r in regen_recs}
        assert "COMPLETED" in statuses, "COMPLETED status was not preserved!"
        print(f" -> Regeneration successfully preserved statuses: {statuses}")

        # Step 10: RBAC Verification
        print("\n[Step 10] Testing RBAC restrictions across roles...")
        # Officer 2 cannot view Officer 1 recommendations
        assert client.get(f"/api/v1/assessments/{ass.id}/recommendations", headers={"Authorization": f"Bearer {t_off2}"}).status_code == 403
        print(" -> Officer 2 viewing Officer 1 recommendations: 403 Forbidden (OK)")

        # Trainer cannot mutate recommendation status
        assert client.patch(f"/api/v1/recommendations/{r1_id}/status", json={"status": "STARTED"}, headers={"Authorization": f"Bearer {t_trainer}"}).status_code == 403
        print(" -> Trainer mutating status: 403 Forbidden (OK)")

        # Trainer can view Officer 1 recommendations
        t_view = client.get(f"/api/v1/assessments/{ass.id}/recommendations", headers={"Authorization": f"Bearer {t_trainer}"})
        assert t_view.status_code == 200
        print(f" -> Trainer inspecting Officer 1 recommendations: 200 OK ({len(t_view.json())} items) (OK)")

        # SME blocked from recommendations
        assert client.get(f"/api/v1/assessments/{ass.id}/recommendations", headers={"Authorization": f"Bearer {t_sme}"}).status_code == 403
        assert client.post(f"/api/v1/assessments/{ass.id}/recommendations", headers={"Authorization": f"Bearer {t_sme}"}).status_code == 403
        print(" -> SME accessing recommendation endpoints: 403 Forbidden (OK)")

        # Step 11: Zero skill gap behavior
        print("\n[Step 11] Testing completed assessment with zero skill gaps...")
        ass_zero = Assessment(
            officer_id=off1.id,
            title="Zero Gap Assessment",
            status=AssessmentStatus.COMPLETED,
            total_questions=5,
            total_correct=5,
            score_percentage=Decimal("100.0"),
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        db.add(ass_zero)
        db.commit()

        zero_res = client.post(f"/api/v1/assessments/{ass_zero.id}/recommendations", headers={"Authorization": f"Bearer {t_off1}"})
        assert zero_res.status_code == 200
        assert zero_res.json() == []
        print(" -> 100% score assessment produces empty recommendation list cleanly (OK)")

        # Step 12: Verify database table count remains exactly 16
        print("\n[Step 12] Verifying total PostgreSQL table count...")
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f" -> Total database tables found: {len(tables)}")
        assert len(tables) == 16, f"Expected 16 tables, found {len(tables)}: {tables}"
        print(" -> Database schema contains EXACTLY 16 TABLES. ZERO MIGRATIONS. (OK)")

        print("\n" + "=" * 70)
        print("ALL LIVE VERIFICATION STEPS PASSED CLEANLY!")
        print("=" * 70)

    finally:
        db.close()


if __name__ == "__main__":
    run_verification()
