from datetime import timedelta
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.db.seed import seed_roles
from app.db.session import SessionLocal
from app.main import app
from app.models.enums import RoleName
from app.models.role import Role
from app.models.user import User

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_roles():
    """Ensure system roles are seeded before running authentication tests."""
    db = SessionLocal()
    try:
        seed_roles(db)
    finally:
        db.close()


def unique_email(prefix: str = "user") -> str:
    """Generate a unique email to isolate test accounts."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}@mospi.test"


# 1. Successful TRAINER registration
def test_successful_trainer_registration():
    email = unique_email("trainer")
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Arun Kumar",
            "email": email,
            "password": "StrongPassword123!",
            "role": "TRAINER",
            "department": "Training Division",
            "designation": "Senior Trainer",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == email.lower()
    assert data["role"] == "TRAINER"
    assert "password" not in data
    assert "password_hash" not in data


# 2. Successful SME registration
def test_successful_sme_registration():
    email = unique_email("sme")
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Dr. Priya Sharma",
            "email": email,
            "password": "StrongPassword123!",
            "role": "SME",
            "department": "National Accounts",
            "designation": "Director",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == email.lower()
    assert data["role"] == "SME"


# 3. Successful OFFICER registration
def test_successful_officer_registration():
    email = unique_email("officer")
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Rajesh Verma",
            "email": email,
            "password": "StrongPassword123!",
            "role": "OFFICER",
            "department": "Field Operations Division",
            "designation": "Assistant Director",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == email.lower()
    assert data["role"] == "OFFICER"


# 4. ADMIN registration rejected
def test_admin_registration_rejected():
    email = unique_email("admin")
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Malicious Admin",
            "email": email,
            "password": "Password123!",
            "role": "ADMIN",
        },
    )
    assert response.status_code in [400, 422]
    assert "password_hash" not in response.text


# 5. Duplicate email rejected (HTTP 409)
def test_duplicate_email_rejected():
    email = unique_email("dup")
    payload = {
        "name": "Original User",
        "email": email,
        "password": "Password123!",
        "role": "OFFICER",
    }
    r1 = client.post("/api/v1/auth/register", json=payload)
    assert r1.status_code == 201

    r2 = client.post("/api/v1/auth/register", json=payload)
    assert r2.status_code == 409
    assert "already exists" in r2.json()["detail"].lower()


# 6. Password is appropriately hashed and verifiable with Argon2
def test_password_is_hashed_not_plaintext():
    email = unique_email("hash_check")
    plain = "SuperSecretPwd!"
    r = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Hash Check",
            "email": email,
            "password": plain,
            "role": "OFFICER",
        },
    )
    assert r.status_code == 201

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email.lower()).first()
        assert user is not None
        assert user.password_hash != plain
        assert user.password_hash.startswith("$argon2")
        assert verify_password(plain, user.password_hash) is True
    finally:
        db.close()


# 7. Plain password and password_hash are never returned in response
def test_plain_password_never_returned():
    email = unique_email("pwd_leak_check")
    r = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Leak Check",
            "email": email,
            "password": "PlainPassword123!",
            "role": "OFFICER",
        },
    )
    data = r.json()
    assert "password" not in data
    assert "password_hash" not in data
    assert "PlainPassword123!" not in r.text


# 8. Successful login
def test_successful_login():
    email = unique_email("login_success")
    password = "CorrectPassword123!"
    client.post(
        "/api/v1/auth/register",
        json={"name": "Login User", "email": email, "password": password, "role": "OFFICER"},
    )

    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == email.lower()
    assert data["user"]["role"] == "OFFICER"
    assert "password_hash" not in data["user"]


# 9. Wrong password rejected (HTTP 401 with generic message)
def test_wrong_password_rejected():
    email = unique_email("wrong_pwd")
    client.post(
        "/api/v1/auth/register",
        json={"name": "User", "email": email, "password": "CorrectPassword!", "role": "OFFICER"},
    )

    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "WrongPassword!"},
    )
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


# 10. Unknown email rejected (HTTP 401 with identical generic message)
def test_unknown_email_rejected():
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "non_existent_12345@mospi.test", "password": "AnyPassword!"},
    )
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


# 11. Inactive user rejected (HTTP 403)
def test_inactive_user_rejected():
    email = unique_email("inactive")
    password = "Password123!"
    client.post(
        "/api/v1/auth/register",
        json={"name": "Inactive User", "email": email, "password": password, "role": "OFFICER"},
    )

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email.lower()).first()
        user.is_active = False
        db.commit()
    finally:
        db.close()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 403
    assert "inactive" in response.json()["detail"].lower()


# 12. Valid JWT accepted on protected endpoint
def test_valid_jwt_accepted():
    email = unique_email("jwt_user")
    password = "Password123!"
    client.post(
        "/api/v1/auth/register",
        json={"name": "JWT User", "email": email, "password": password, "role": "OFFICER"},
    )
    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    token = login_resp.json()["access_token"]

    response = client.get(
        "/api/v1/test/authenticated",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "authenticated"
    assert response.json()["email"] == email.lower()


# 13. Missing JWT rejected (HTTP 401)
def test_missing_jwt_rejected():
    response = client.get("/api/v1/test/authenticated")
    assert response.status_code == 401


# 14. Invalid JWT rejected (HTTP 401)
def test_invalid_jwt_rejected():
    response = client.get(
        "/api/v1/test/authenticated",
        headers={"Authorization": "Bearer invalid.jwt.token"},
    )
    assert response.status_code == 401


# 15. Expired JWT rejected (HTTP 401)
def test_expired_jwt_rejected():
    email = unique_email("expired_user")
    password = "Password123!"
    reg = client.post(
        "/api/v1/auth/register",
        json={"name": "Expired User", "email": email, "password": password, "role": "OFFICER"},
    )
    user_id = reg.json()["id"]

    # Generate token already expired 5 minutes ago
    expired_token = create_access_token(
        data={"sub": str(user_id), "role": "OFFICER"},
        expires_delta=timedelta(minutes=-5),
    )

    response = client.get(
        "/api/v1/test/authenticated",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


# 16. /me returns current user
def test_get_me_returns_current_user():
    email = unique_email("me_user")
    password = "Password123!"
    client.post(
        "/api/v1/auth/register",
        json={
            "name": "Me User",
            "email": email,
            "password": password,
            "role": "OFFICER",
            "department": "National Sample Survey",
            "designation": "Survey Officer",
        },
    )
    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    token = login_resp.json()["access_token"]

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Me User"
    assert data["email"] == email.lower()
    assert data["role"] == "OFFICER"
    assert data["department"] == "National Sample Survey"
    assert data["designation"] == "Survey Officer"
    assert data["is_active"] is True
    assert "password_hash" not in data


# Helper to create and authenticate a user with specific role
def create_authenticated_user(role: str) -> str:
    email = unique_email(role.lower())
    password = "Password123!"
    if role == "ADMIN":
        # Create controlled admin via database seed mechanism
        db = SessionLocal()
        try:
            admin_role = db.query(Role).filter_by(name=RoleName.ADMIN.value).first()
            from app.core.security import hash_password
            admin_user = User(
                name="System Administrator",
                email=email,
                password_hash=hash_password(password),
                role_id=admin_role.id,
                is_active=True,
            )
            db.add(admin_user)
            db.commit()
        finally:
            db.close()
    else:
        client.post(
            "/api/v1/auth/register",
            json={"name": f"{role} User", "email": email, "password": password, "role": role},
        )

    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return login_resp.json()["access_token"]


# 17. TRAINER endpoint accepts TRAINER
def test_trainer_endpoint_accepts_trainer():
    token = create_authenticated_user("TRAINER")
    response = client.get("/api/v1/test/trainer", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["role"] == "TRAINER"


# 18. TRAINER endpoint rejects OFFICER (HTTP 403)
def test_trainer_endpoint_rejects_officer():
    token = create_authenticated_user("OFFICER")
    response = client.get("/api/v1/test/trainer", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


# 19. SME endpoint accepts SME
def test_sme_endpoint_accepts_sme():
    token = create_authenticated_user("SME")
    response = client.get("/api/v1/test/sme", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["role"] == "SME"


# 20. OFFICER endpoint accepts OFFICER
def test_officer_endpoint_accepts_officer():
    token = create_authenticated_user("OFFICER")
    response = client.get("/api/v1/test/officer", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["role"] == "OFFICER"


# 21. ADMIN endpoint accepts ADMIN
def test_admin_endpoint_accepts_admin():
    token = create_authenticated_user("ADMIN")
    response = client.get("/api/v1/test/admin", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["role"] == "ADMIN"


# 22. Non-admin cannot access ADMIN endpoint
def test_non_admin_cannot_access_admin_endpoint():
    officer_token = create_authenticated_user("OFFICER")
    r1 = client.get("/api/v1/test/admin", headers={"Authorization": f"Bearer {officer_token}"})
    assert r1.status_code == 403

    trainer_token = create_authenticated_user("TRAINER")
    r2 = client.get("/api/v1/test/admin", headers={"Authorization": f"Bearer {trainer_token}"})
    assert r2.status_code == 403


# Additional Security Tests
def test_login_ignores_or_rejects_role_spoofing():
    """Verify client cannot change or inject role during login."""
    email = unique_email("role_spoof")
    password = "Password123!"
    client.post(
        "/api/v1/auth/register",
        json={"name": "Spoofer", "email": email, "password": password, "role": "OFFICER"},
    )
    # Attempt to send role='ADMIN' in login payload
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password, "role": "ADMIN"},
    )
    assert login_resp.status_code == 200
    # The returned token and profile must still have the DB role: OFFICER
    assert login_resp.json()["user"]["role"] == "OFFICER"

    token = login_resp.json()["access_token"]
    admin_check = client.get("/api/v1/test/admin", headers={"Authorization": f"Bearer {token}"})
    assert admin_check.status_code == 403


def test_jwt_secret_loaded_from_settings():
    """Verify JWT secret is configured in application settings and not empty."""
    assert len(settings.JWT_SECRET_KEY) >= 32
    assert settings.JWT_ALGORITHM == "HS256"


# OAuth2 /token and Swagger Compatibility Tests
def test_oauth2_token_endpoint_successful_authentication():
    """Verify /api/v1/auth/token accepts OAuth2 form credentials and returns valid JWT."""
    email = unique_email("oauth2_user")
    password = "OAuth2Password123!"
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={"name": "OAuth2 User", "email": email, "password": password, "role": "TRAINER"},
    )
    assert reg_resp.status_code == 201

    # Send form data (application/x-www-form-urlencoded) with username and password
    token_resp = client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": password},
    )
    assert token_resp.status_code == 200
    data = token_resp.json()
    assert "access_token" in data
    assert data["token_type"].lower() == "bearer"
    assert "user" in data
    assert data["user"]["role"] == "TRAINER"
    assert data["user"]["email"] == email.lower()


def test_oauth2_token_endpoint_invalid_credentials():
    """Verify /api/v1/auth/token rejects invalid password."""
    email = unique_email("oauth2_bad")
    password = "CorrectPassword123!"
    client.post(
        "/api/v1/auth/register",
        json={"name": "OAuth2 Bad", "email": email, "password": password, "role": "OFFICER"},
    )

    token_resp = client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": "WrongPassword!"},
    )
    assert token_resp.status_code == 401
    assert "Invalid email or password" in token_resp.json()["detail"]


def test_protected_endpoints_accept_token_from_oauth2_endpoint():
    """Verify JWT returned by /api/v1/auth/token authorizes protected endpoints."""
    email = unique_email("oauth2_auth")
    password = "ValidPassword123!"
    client.post(
        "/api/v1/auth/register",
        json={"name": "Auth User", "email": email, "password": password, "role": "SME"},
    )

    token_resp = client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": password},
    )
    assert token_resp.status_code == 200
    token = token_resp.json()["access_token"]

    # Call /api/v1/auth/me
    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == email.lower()
    assert me_resp.json()["role"] == "SME"

    # Call role-specific test endpoint /api/v1/test/sme
    sme_resp = client.get("/api/v1/test/sme", headers={"Authorization": f"Bearer {token}"})
    assert sme_resp.status_code == 200


def test_swagger_openapi_points_oauth2_to_auth_token():
    """Verify OpenAPI security scheme points OAuth2PasswordBearer to /api/v1/auth/token."""
    openapi_schema = app.openapi()
    security_schemes = openapi_schema["components"]["securitySchemes"]
    assert "OAuth2PasswordBearer" in security_schemes
    oauth2_scheme = security_schemes["OAuth2PasswordBearer"]
    assert oauth2_scheme["type"] == "oauth2"
    assert oauth2_scheme["flows"]["password"]["tokenUrl"] == "/api/v1/auth/token"


def test_existing_json_login_endpoint_continues_to_work():
    """Verify existing /api/v1/auth/login JSON endpoint remains fully functional."""
    email = unique_email("json_login")
    password = "JsonPartPassword123!"
    client.post(
        "/api/v1/auth/register",
        json={"name": "JSON User", "email": email, "password": password, "role": "TRAINER"},
    )

    # Call /api/v1/auth/login with JSON
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_resp.status_code == 200
    data = login_resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["role"] == "TRAINER"

    token = data["access_token"]
    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == email.lower()
