# StatKarmayogi — Phase 3 Implementation Report: Authentication & Authorization

**Smart India Hackathon 2026**  
- **Problem Statement ID**: SIH26101  
- **Organization**: Ministry of Statistics and Programme Implementation (MoSPI)  
- **Status**: Phase 3 Completed & Fully Verified  

---

## 1. Files Created
1. `app/core/security.py`: Argon2 password hashing (`hash_password`, `verify_password`) and JWT token utilities (`create_access_token`, `decode_access_token`).
2. `app/core/dependencies.py`: Reusable FastAPI dependencies `get_current_user` (extracts Bearer token, validates JWT, fetches authoritative active user from DB) and `require_roles` (role verification factory).
3. `app/schemas/auth.py`: Pydantic v2 schemas for registration (`UserRegisterRequest`), login (`UserLoginRequest`), and token payload (`TokenResponse`).
4. `app/schemas/user.py`: Safe user response schemas (`UserResponse`, `UserMeResponse`) strictly excluding sensitive credentials.
5. `app/services/auth_service.py`: Business logic for user registration, authentication, and token generation.
6. `app/routers/auth.py`: Authentication endpoints (`POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET /api/v1/auth/me`).
7. `app/routers/verification.py`: Isolated role-based test endpoints (`GET /api/v1/test/{authenticated, trainer, sme, officer, admin}`).
8. `tests/test_auth.py`: 24 unit and security tests covering all authentication scenarios.
9. `pytest.ini`: Pytest configuration directing test discovery to `tests/`.

---

## 2. Files Modified
1. `requirements.txt`: Added `pyjwt>=2.8.0` and `argon2-cffi>=23.1.0`.
2. `app/core/config.py`: Added `JWT_SECRET_KEY`, `JWT_ALGORITHM`, and `ACCESS_TOKEN_EXPIRE_MINUTES`.
3. `.env.example`: Documented JWT configuration parameters.
4. `.env`: Configured 64-character development `JWT_SECRET_KEY`.
5. `app/schemas/__init__.py`: Exported authentication and user schemas.
6. `app/services/__init__.py`: Exported `AuthService`.
7. `app/routers/__init__.py`: Exported `auth_router` and `verification_router`.
8. `app/main.py`: Included `auth_router` and `verification_router` under prefix `/api/v1`.
9. `backend/README.md`: Documented authentication architecture, endpoints, role rules, and security guidelines.

---

## 3. Dependencies Added
- `argon2-cffi` (25.1.0): Industry-standard password hashing algorithm.
- `pyjwt` (2.15.0): Secure JSON Web Token encoding, decoding, and signature verification.

---

## 4. Authentication Architecture
- **Stateless Bearer JWT**: Tokens contain `sub` (User ID string), `role` (Role name), `iat` (issued at), and `exp` (expiration).
- **Authoritative Database Lookups**: The client-provided JWT is validated against cryptographic signature and expiration. Then, `get_current_user` queries the PostgreSQL `users` table to ensure the user exists and `is_active=True`.
- **Role Isolation**: Role verification never trusts client claims. It relies directly on `current_user.role.name` resolved from the authoritative relational `roles` table.

---

## 5. Registration Flow
- **Endpoint**: `POST /api/v1/auth/register` (Status: `201 Created`)
- **Payload**:
  ```json
  {
    "name": "Dr. Priya Sharma",
    "email": "priya.sharma@mospi.gov.in",
    "password": "StrongPassword123!",
    "role": "SME",
    "department": "National Accounts Division",
    "designation": "Director"
  }
  ```
- **Execution Steps**:
  1. Validates schema and normalizes email (`lower()`, `strip()`).
  2. Ensures role is one of `TRAINER`, `SME`, `OFFICER`. Rejects `ADMIN` with `HTTP 400 Bad Request`.
  3. Checks for existing email in `users` (case-insensitive). Duplicate raises `HTTP 409 Conflict`.
  4. Resolves role name against `roles` table to retrieve `role_id`.
  5. Hashes password using Argon2id (`$argon2id$...`).
  6. Inserts user with `is_active=True`.
  7. Returns safe user metadata without `password_hash`.

---

## 6. Login Flow
- **Endpoint**: `POST /api/v1/auth/login` (Status: `200 OK`)
- **Payload**:
  ```json
  {
    "email": "priya.sharma@mospi.gov.in",
    "password": "StrongPassword123!"
  }
  ```
  *(Notice: Absolutely NO role field in login request).*
- **Execution Steps**:
  1. Normalizes email.
  2. Looks up user by email in PostgreSQL.
  3. Verifies password against `password_hash` using Argon2.
  4. If email is not found or password does not match, returns generic `HTTP 401 Unauthorized` ("Invalid email or password.") to prevent user enumeration.
  5. Verifies `user.is_active`. If false, returns `HTTP 403 Forbidden` ("Account is inactive.").
  6. Reads the user's stored role from `roles` table.
  7. Signs and returns JWT access token along with safe user profile.

---

## 7. JWT Configuration
- `JWT_SECRET_KEY`: Configured via environment variables; min 32 characters (256-bit entropy).
- `JWT_ALGORITHM`: `HS256`.
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Default 60 minutes.

---

## 8. Authorization Implementation
- **`require_roles(*allowed_roles)`**: Dependency factory checking user role:
  - If user holds the required role, request continues.
  - If user role is not permitted, raises `HTTP 403 Forbidden` ("Operation not permitted. Required role: ...").
- **Verification Endpoints Tested**:
  - `GET /api/v1/test/authenticated`: Any valid active user.
  - `GET /api/v1/test/trainer`: Restricted to `TRAINER`.
  - `GET /api/v1/test/sme`: Restricted to `SME`.
  - `GET /api/v1/test/officer`: Restricted to `OFFICER`.
  - `GET /api/v1/test/admin`: Restricted to `ADMIN`.

---

## 9. Tests Executed & Results
Ran full automated test suite via `python -m pytest -v`:
- 5 foundation tests (`test_health.py`)
- 10 database schema & constraint tests (`test_models.py`)
- 24 authentication, authorization, and security tests (`test_auth.py`)

```text
tests/test_auth.py::test_successful_trainer_registration PASSED          [  2%]
tests/test_auth.py::test_successful_sme_registration PASSED              [  5%]
tests/test_auth.py::test_successful_officer_registration PASSED          [  7%]
tests/test_auth.py::test_admin_registration_rejected PASSED              [ 10%]
tests/test_auth.py::test_duplicate_email_rejected PASSED                 [ 12%]
tests/test_auth.py::test_password_is_hashed_not_plaintext PASSED         [ 15%]
tests/test_auth.py::test_plain_password_never_returned PASSED            [ 17%]
tests/test_auth.py::test_successful_login PASSED                         [ 20%]
tests/test_auth.py::test_wrong_password_rejected PASSED                  [ 23%]
tests/test_auth.py::test_unknown_email_rejected PASSED                   [ 25%]
tests/test_auth.py::test_inactive_user_rejected PASSED                   [ 28%]
tests/test_auth.py::test_valid_jwt_accepted PASSED                       [ 30%]
tests/test_auth.py::test_missing_jwt_rejected PASSED                     [ 33%]
tests/test_auth.py::test_invalid_jwt_rejected PASSED                     [ 35%]
tests/test_auth.py::test_expired_jwt_rejected PASSED                     [ 38%]
tests/test_auth.py::test_get_me_returns_current_user PASSED              [ 41%]
tests/test_auth.py::test_trainer_endpoint_accepts_trainer PASSED         [ 43%]
tests/test_auth.py::test_trainer_endpoint_rejects_officer PASSED         [ 46%]
tests/test_auth.py::test_sme_endpoint_accepts_sme PASSED                 [ 48%]
tests/test_auth.py::test_officer_endpoint_accepts_officer PASSED         [ 51%]
tests/test_auth.py::test_admin_endpoint_accepts_admin PASSED             [ 53%]
tests/test_auth.py::test_non_admin_cannot_access_admin_endpoint PASSED   [ 56%]
tests/test_auth.py::test_login_ignores_or_rejects_role_spoofing PASSED   [ 58%]
tests/test_auth.py::test_jwt_secret_loaded_from_settings PASSED          [ 61%]
tests/test_health.py::test_app_import PASSED                             [ 64%]
tests/test_health.py::test_read_root PASSED                              [ 66%]
tests/test_health.py::test_health_check PASSED                           [ 69%]
tests/test_health.py::test_settings_loaded PASSED                        [ 71%]
tests/test_health.py::test_database_configuration PASSED                 [ 74%]
tests/test_models.py::test_all_15_tables_exist_in_metadata PASSED        [ 76%]
tests/test_models.py::test_all_15_tables_exist_in_database PASSED        [ 79%]
tests/test_models.py::test_role_seed_creates_exactly_4_roles PASSED      [ 82%]
tests/test_models.py::test_user_email_unique_constraint PASSED           [ 84%]
tests/test_models.py::test_competency_code_unique_constraint PASSED      [ 87%]
tests/test_models.py::test_course_igot_id_unique_constraint PASSED       [ 89%]
tests/test_models.py::test_course_competency_unique_constraint PASSED    [ 92%]
tests/test_models.py::test_assessment_question_unique_constraint PASSED  [ 94%]
tests/test_models.py::test_answer_unique_constraint PASSED               [ 97%]
tests/test_models.py::test_full_relational_lifecycle PASSED              [100%]

============================= 39 passed in 2.71s ==============================
```

---

## 10. Manual Workflow Verification
Executed automated test runner simulating live client interactions across all 4 personas:
- **`TRAINER`**: Registered (201) $\rightarrow$ Logged in (200) $\rightarrow$ JWT issued $\rightarrow$ `GET /api/v1/auth/me` (200, role: `TRAINER`) $\rightarrow$ Accessed `GET /api/v1/test/trainer` (200).
- **`SME`**: Registered (201) $\rightarrow$ Logged in (200) $\rightarrow$ JWT issued $\rightarrow$ `GET /api/v1/auth/me` (200, role: `SME`) $\rightarrow$ Accessed `GET /api/v1/test/sme` (200).
- **`OFFICER`**: Registered (201) $\rightarrow$ Logged in (200) $\rightarrow$ JWT issued $\rightarrow$ `GET /api/v1/auth/me` (200, role: `OFFICER`) $\rightarrow$ Accessed `GET /api/v1/test/officer` (200).
- **`ADMIN`**: Created via controlled admin seed $\rightarrow$ Logged in (200) $\rightarrow$ JWT issued $\rightarrow$ `GET /api/v1/auth/me` (200, role: `ADMIN`) $\rightarrow$ Accessed `GET /api/v1/test/admin` (200). Cross-role checks confirmed that non-admin accounts receive `HTTP 403 Forbidden` on `/test/admin`.

---

## 11. Database Changes
- **No schema modifications required**. The Phase 2 15-entity schema (`roles` and `users` tables) perfectly satisfied all Phase 3 requirements.

---

## 12. Security Verification
- **Password Hashes**: Hashed with Argon2id; passwords never stored or returned in plaintext.
- **Credential Leaks**: `password_hash` is omitted from all Pydantic response models (`UserResponse`, `UserMeResponse`, `TokenResponse`).
- **Role Tampering**: Role cannot be altered via login requests; authoritative database role is always read.
- **Timing & Enumeration Attacks**: Login failure returns a uniform `HTTP 401` ("Invalid email or password.") regardless of whether the email or password was wrong.
- **Deactivated Users**: Inactive accounts are blocked with `HTTP 403` at both login and Bearer token dependency levels.

---

## 13. Unresolved Issues
- None. Phase 3 is fully operational and verified.

---

**Confirmation**: No later-phase functionality (documents upload, RAG, ChromaDB, Mistral MCQ generation, SME review, assessments, scoring, courses, or frontend) was implemented.
