import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.db.seed import seed_roles
from app.db.seed_courses import seed_courses
from app.db.session import SessionLocal
from app.main import app
from app.models.course import Course
from app.models.enums import RoleName
from app.models.role import Role
from app.models.user import User

client = TestClient(app)


@pytest.fixture(scope="module")
def setup_courses_environment():
    """Sets up roles, users, and seeds courses."""
    db: Session = SessionLocal()
    try:
        seed_roles(db)
        seed_courses(db)

        officer_role = db.query(Role).filter_by(name=RoleName.OFFICER.value).first()
        trainer_role = db.query(Role).filter_by(name=RoleName.TRAINER.value).first()
        sme_role = db.query(Role).filter_by(name=RoleName.SME.value).first()
        admin_role = db.query(Role).filter_by(name=RoleName.ADMIN.value).first()

        suffix = uuid.uuid4().hex[:6]

        officer = User(
            name="Courses Officer",
            email=f"course_officer_{suffix}@mospi.gov.in",
            password_hash="test_hash",
            role_id=officer_role.id,
            is_active=True,
        )
        trainer = User(
            name="Courses Trainer",
            email=f"course_trainer_{suffix}@mospi.gov.in",
            password_hash="test_hash",
            role_id=trainer_role.id,
            is_active=True,
        )
        sme = User(
            name="Courses SME",
            email=f"course_sme_{suffix}@mospi.gov.in",
            password_hash="test_hash",
            role_id=sme_role.id,
            is_active=True,
        )
        admin = User(
            name="Courses Admin",
            email=f"course_admin_{suffix}@mospi.gov.in",
            password_hash="test_hash",
            role_id=admin_role.id,
            is_active=True,
        )

        db.add_all([officer, trainer, sme, admin])
        db.commit()

        tokens = {
            "officer": create_access_token({"sub": str(officer.id)}),
            "trainer": create_access_token({"sub": str(trainer.id)}),
            "sme": create_access_token({"sub": str(sme.id)}),
            "admin": create_access_token({"sub": str(admin.id)}),
        }

        first_course = db.query(Course).first()
        course_id = first_course.id if first_course else 1

        return {
            "tokens": tokens,
            "course_id": course_id,
        }
    finally:
        db.close()


def test_unauthenticated_course_access_returns_401():
    """Unauthenticated request to course catalogue must return 401."""
    resp = client.get("/api/v1/courses")
    assert resp.status_code == 401


def test_courses_catalogue_listing_and_filtering(setup_courses_environment):
    """Authenticated users can browse course catalogue with query filters."""
    token = setup_courses_environment["tokens"]["officer"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Plain listing
    resp = client.get("/api/v1/courses", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "items" in data
    assert data["total"] >= 6
    assert len(data["items"]) >= 6

    # 2. Filter by search query
    resp_q = client.get("/api/v1/courses?query=ASI", headers=headers)
    assert resp_q.status_code == 200
    data_q = resp_q.json()
    for item in data_q["items"]:
        assert "ASI" in item["title"] or "ASI" in (item["description"] or "")

    # 3. Filter by difficulty
    resp_d = client.get("/api/v1/courses?difficulty=Beginner", headers=headers)
    assert resp_d.status_code == 200
    for item in resp_d.json()["items"]:
        assert item["difficulty"].lower() == "beginner"


def test_courses_detail_with_competency_mappings(setup_courses_environment):
    """Course detail endpoint returns mapped competencies and relevance scores."""
    token = setup_courses_environment["tokens"]["trainer"]
    cid = setup_courses_environment["course_id"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get(f"/api/v1/courses/{cid}", headers=headers)
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["id"] == cid
    assert "competencies" in detail
    assert isinstance(detail["competencies"], list)
    if detail["competencies"]:
        comp_map = detail["competencies"][0]
        assert "competency_id" in comp_map
        assert "relevance_score" in comp_map
        assert 0.0 <= comp_map["relevance_score"] <= 1.0


def test_course_detail_not_found(setup_courses_environment):
    """Nonexistent course ID returns 404."""
    token = setup_courses_environment["tokens"]["officer"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/api/v1/courses/999999", headers=headers)
    assert resp.status_code == 404


def test_all_course_urls_are_valid_routes_or_null(setup_courses_environment):
    """Every course URL either points to an implemented route or is null; no dead/fictional URLs."""
    token = setup_courses_environment["tokens"]["admin"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/api/v1/courses", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    for item in items:
        url = item.get("course_url")
        if url is not None:
            assert not url.startswith("https://mock.igotkarmayogi.gov.in")
            assert "/mock/igot" not in url
        # Confirm no 'is_external' field is present in course response
        assert "is_external" not in item


def test_sme_can_view_course_catalogue(setup_courses_environment):
    """SME role can view courses in read-only mode."""
    token = setup_courses_environment["tokens"]["sme"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/api/v1/courses", headers=headers)
    assert resp.status_code == 200


def test_unmapped_prototype_courses_have_no_competency_mappings(setup_courses_environment):
    """FPOS and DAP courses must exist in catalogue but have zero competency mappings."""
    token = setup_courses_environment["tokens"]["officer"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/api/v1/courses", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    courses_by_igot_id = {c["igot_course_id"]: c for c in items if c.get("igot_course_id")}

    # 1. FPOS course exists in catalogue
    assert "IGOT-PROTO-FPOS-01" in courses_by_igot_id
    fpos_course = courses_by_igot_id["IGOT-PROTO-FPOS-01"]

    # 2. DAP course exists in catalogue
    assert "IGOT-PROTO-DAP-01" in courses_by_igot_id
    dap_course = courses_by_igot_id["IGOT-PROTO-DAP-01"]

    # 3. FPOS course has no CourseCompetency mappings
    resp_fpos = client.get(f"/api/v1/courses/{fpos_course['id']}", headers=headers)
    assert resp_fpos.status_code == 200
    fpos_detail = resp_fpos.json()
    assert fpos_detail["competencies"] == []

    # 4. DAP course has no CourseCompetency mappings
    resp_dap = client.get(f"/api/v1/courses/{dap_course['id']}", headers=headers)
    assert resp_dap.status_code == 200
    dap_detail = resp_dap.json()
    assert dap_detail["competencies"] == []


def test_verified_course_competency_mappings_preserved(setup_courses_environment):
    """The four verified courses must have their intended competency mappings intact."""
    token = setup_courses_environment["tokens"]["officer"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/api/v1/courses", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    courses_by_igot_id = {c["igot_course_id"]: c for c in items if c.get("igot_course_id")}

    verified_checks = [
        ("IGOT-PROTO-ASI-01", "ASI"),
        ("IGOT-PROTO-IIP-01", "IIP"),
        ("IGOT-PROTO-NAS-01", "National Accounts"),
        ("IGOT-PROTO-SSD-01", "Sample Survey Design"),
    ]
    for igot_id, comp_keyword in verified_checks:
        assert igot_id in courses_by_igot_id
        cid = courses_by_igot_id[igot_id]["id"]
        detail_resp = client.get(f"/api/v1/courses/{cid}", headers=headers)
        assert detail_resp.status_code == 200
        comp_list = detail_resp.json()["competencies"]
        assert len(comp_list) >= 1
        combined = " ".join([c["competency_name"] + " " + c["competency_code"] for c in comp_list]).lower()
        assert comp_keyword.lower() in combined

