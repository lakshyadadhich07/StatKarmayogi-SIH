# StatKarmayogi — Phase 1–5 System Verification Report
## Comprehensive Read-Only Inspection for pgAdmin & Swagger UI Verification

**Smart India Hackathon 2026**  
- **Problem Statement ID**: SIH26101  
- **Target Organization**: Ministry of Statistics and Programme Implementation (MoSPI)  
- **Scope**: Phases 1–5 Backend Verification (Read-Only)  
- **Inspection Date**: September 26, 2026  

---

## 1. PostgreSQL / pgAdmin Connection Information

| Parameter | Configuration Value | Notes |
| :--- | :--- | :--- |
| **Host** | `localhost` or `127.0.0.1` | Local PostgreSQL instance |
| **Port** | `5432` | Standard PostgreSQL port |
| **Database Name** | `statkarmayogi_db` | Primary application database |
| **Username** | `postgres` | Superuser / database owner |
| **SSL Mode** | `prefer` / `disable` | Local development connection (no SSL certificate required) |
| **Password Location** | `c:\SIH\backend\.env` | Specified within the `DATABASE_URL` connection string |
| **Password Status** | **Configured & Active** | The application connects successfully to PostgreSQL |

> [!NOTE]
> **Safe Development Password Instructions (if needed for pgAdmin):**  
> If your pgAdmin installation prompts for a password that differs from your local Windows PostgreSQL service:
> 1. Open PowerShell / Command Prompt as administrator or launch `psql -U postgres`.
> 2. Run the SQL statement:
>    ```sql
>    ALTER USER postgres WITH PASSWORD 'your_dev_password';
>    ```
> 3. Update the password in `c:\SIH\backend\.env`:
>    ```text
>    DATABASE_URL=postgresql+psycopg://postgres:your_dev_password@localhost:5432/statkarmayogi_db
>    ```
> 4. Connect pgAdmin using `your_dev_password`.

---

## 2. PostgreSQL Table Inventory

The live `statkarmayogi_db` database contains **16 tables** in the `public` schema (the 15 core entities plus `courses` for iGOT learning integration).

| Table Name | Primary Key | Key Foreign Keys | Status / Enum Columns | Approx. Rows | Notes |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **`roles`** | `id` | None | None | **4** | Pre-seeded system roles (`TRAINER`, `SME`, `OFFICER`, `ADMIN`) |
| **`users`** | `id` | `role_id` $\rightarrow$ `roles.id` | None (`is_active: bool`) | **440** | Stores user profiles; single authoritative role via `role_id` |
| **`competencies`** | `id` | None | None (`is_active: bool`) | **5** | MoSPI statistical competencies taxonomy |
| **`documents`** | `id` | `uploaded_by` $\rightarrow$ `users.id` | `status` (`document_status_enum`) | **125** | Ingested PDF/PPTX learning materials |
| **`document_chunks`**| `id` | `document_id` $\rightarrow$ `documents.id` | None | **161** | Chunk text metadata with `chroma_id` traceability |
| **`questions`** | `id` | `document_id` $\rightarrow$ `documents.id`<br>`competency_id` $\rightarrow$ `competencies.id`<br>`source_chunk_id` $\rightarrow$ `document_chunks.id`<br>`created_by` $\rightarrow$ `users.id` | `status` (`question_status_enum`)<br>`difficulty` (`question_difficulty_enum`) | **33** | AI-generated grounded MCQs with chunk attribution |
| **`question_reviews`**| `id` | `question_id` $\rightarrow$ `questions.id`<br>`reviewer_id` $\rightarrow$ `users.id` | `action` (`review_action_enum`) | **0** | Phase 6 SME review & audit table (ready for use) |
| **`courses`** | `id` | None | None | **0** | iGOT Karmayogi course catalog |
| **`course_competencies`**| `id`| `course_id` $\rightarrow$ `courses.id`<br>`competency_id` $\rightarrow$ `competencies.id` | None | **0** | M:N mapping between courses and competencies |
| **`assessments`** | `id` | `officer_id` $\rightarrow$ `users.id` | `status` (`assessment_status_enum`) | **0** | Diagnostic and post-learning assessments |
| **`assessment_questions`**| `id`| `assessment_id` $\rightarrow$ `assessments.id`<br>`question_id` $\rightarrow$ `questions.id` | None | **0** | Questions assigned to an assessment |
| **`assessment_attempts`**| `id`| `assessment_id` $\rightarrow$ `assessments.id`<br>`officer_id` $\rightarrow$ `users.id` | None | **0** | Officer test attempt instances |
| **`answers`** | `id` | `attempt_id` $\rightarrow$ `assessment_attempts.id`<br>`question_id` $\rightarrow$ `questions.id` | None | **0** | Individual question responses recorded |
| **`competency_results`**| `id` | `assessment_id` $\rightarrow$ `assessments.id`<br>`competency_id` $\rightarrow$ `competencies.id` | `proficiency_level` (`proficiency_level_enum`) | **0** | Post-assessment competency score breakdown |
| **`skill_gaps`** | `id` | `assessment_id` $\rightarrow$ `assessments.id`<br>`competency_id` $\rightarrow$ `competencies.id` | `gap_level` (`gap_level_enum`) | **0** | Identified competency gaps for adaptive learning |
| **`recommendations`** | `id` | `assessment_id` $\rightarrow$ `assessments.id`<br>`officer_id` $\rightarrow$ `users.id`<br>`competency_id` $\rightarrow$ `competencies.id`<br>`course_id` $\rightarrow$ `courses.id` | `status` (`recommendation_status_enum`) | **0** | Personalized iGOT course recommendations |

### Note on `user_roles`
The prompt mentioned inspecting `user_roles`. In the authoritative Phase 2 & 3 architecture, the system enforces a strict single-role-per-user model by storing `users.role_id` referencing `roles.id`. There is no separate `user_roles` join table; role resolution is deterministic and performed directly via `users.role_id`.

---

## 3. Important Relational Foreign Keys Verified

Every critical relational constraint was inspected directly in the PostgreSQL system catalog (`information_schema.referential_constraints`):

| Relationship | Source Column | Target Column | Delete Rule | Verified Status |
| :--- | :--- | :--- | :--- | :---: |
| **User $\rightarrow$ Uploaded Documents** | `documents.uploaded_by` | `users.id` | `RESTRICT` | **VERIFIED** |
| **Document $\rightarrow$ Chunks** | `document_chunks.document_id` | `documents.id` | `CASCADE` | **VERIFIED** |
| **Document $\rightarrow$ Questions** | `questions.document_id` | `documents.id` | `RESTRICT` | **VERIFIED** |
| **Competency $\rightarrow$ Questions** | `questions.competency_id` | `competencies.id` | `RESTRICT` | **VERIFIED** |
| **Source Chunk $\rightarrow$ Questions** | `questions.source_chunk_id` | `document_chunks.id` | `SET NULL` | **VERIFIED** |
| **Question $\rightarrow$ Reviews** | `question_reviews.question_id` | `questions.id` | `CASCADE` | **VERIFIED** |
| **SME Reviewer $\rightarrow$ Reviews** | `question_reviews.reviewer_id` | `users.id` | `RESTRICT` | **VERIFIED** |

---

## 4. Phase 4 & 5 Data Verification

### Processed Document Check (Live Record: ID 155)
- **Filename**: `asi_manual_2026.pdf`
- **File Type**: `PDF`
- **Status**: `PROCESSED`
- **Generation Count**: `3`
- **Document Chunks**: 3 chunks persisted in PostgreSQL:
  - `Chunk 0`: Page `1`, Content Hash `a602d3c946caf78f...`, Chroma ID `doc_155_chunk_0_a602d3c946caf78f`
  - `Chunk 1`: Page `2`, Content Hash `2075a34e022026ae...`, Chroma ID `doc_155_chunk_1_2075a34e022026ae`
  - `Chunk 2`: Page `3`, Content Hash `f8164f9f74351543...`, Chroma ID `doc_155_chunk_2_f8164f9f74351543`
- **ChromaDB Vector Store Consistency**:
  - Queried collection `statkarmayogi_chunks` for `doc_155_chunk_0_a602d3c946caf78f`.
  - Vector exists and metadata matches:
    ```json
    {
      "document_id": 155,
      "chunk_index": 0,
      "page_number": 1,
      "filename": "asi_manual_2026.pdf",
      "content_hash": "a602d3c946caf78fd5c418205117723511f9d77919d0a3b0bf89a1f9018bdca7"
    }
    ```

### Generated Question Check (Live Record: ID 72)
- **Status**: `PENDING_REVIEW` (Strictly Phase 5 boundary preserved)
- **Document ID**: `155` (Valid foreign key)
- **Source Chunk ID**: `193` (Valid foreign key referencing Chunk 1 of Document 155)
- **Source Page**: `2` (Directly verified against chunk metadata)
- **Generation Model**: `mistral-large-latest`
- **Created By**: `530` (Valid Trainer user ID)
- **Question Prompt**: *"Under ASI methodology (chunk 193), what is the treatment of depreciation?"*
- **Options**: 4 distinct non-empty choices with valid `correct_option = 'A'`.
- **Educational Explanation**: Accurately citations source text from page 2.

---

## 5. Phase 6 Suitability Analysis (`question_reviews`)

The existing database schema was evaluated against the requirements for Phase 6 (Human-in-the-Loop SME Review):

| Required Capability | Supported in Existing Schema? | Details |
| :--- | :---: | :--- |
| **SME Reviewer Identity** | **YES** | `question_reviews.reviewer_id` $\rightarrow$ `users.id` (FK, `RESTRICT`) |
| **Question Association** | **YES** | `question_reviews.question_id` $\rightarrow$ `questions.id` (FK, `CASCADE`) |
| **Review Action / Status** | **YES** | `question_reviews.action` uses PostgreSQL enum `review_action_enum` (`['APPROVE', 'REJECT']`) |
| **Question Status Lifecycle** | **YES** | `questions.status` uses PostgreSQL enum `question_status_enum` (`['PENDING_REVIEW', 'APPROVED', 'REJECTED']`) |
| **Review Comments / Reason** | **YES** | `question_reviews.comment` (`TEXT`, nullable) |
| **Audit Timestamp** | **YES** | `question_reviews.created_at` (`TIMESTAMPTZ`, default `now()`) |
| **Multiple Reviews Audit Log** | **YES** | Schema permits multiple review records per question (1-to-many relationship) |

> [!IMPORTANT]
> The database schema is **100% complete and ready for Phase 6**. Zero database schema modifications, alterations, or migrations are required.

---

## 6. Swagger / OpenAPI Endpoint Inventory

FastAPI exposes interactive API documentation at:
- **Swagger UI**: `http://127.0.0.1:8000/docs`
- **ReDoc**: `http://127.0.0.1:8000/redoc`
- **OpenAPI JSON**: `http://127.0.0.1:8000/openapi.json`

### Group 1: Authentication (`/auth`)

#### 1. `POST /api/v1/auth/register`
- **Auth Required**: No (Public)
- **Allowed Roles**: Any registrant (`TRAINER`, `SME`, `OFFICER`; `ADMIN` blocked)
- **Request Body**: `application/json` (`UserRegisterRequest`: `name`, `email`, `password`, `role`, `department`, `designation`)
- **Response**: `201 Created` (`UserResponse`: `id`, `name`, `email`, `role`)

#### 2. `POST /api/v1/auth/login`
- **Auth Required**: No (Public)
- **Allowed Roles**: Any registered active user
- **Request Body**: `application/json` (`UserLoginRequest`: `email`, `password` — strictly no role parameter)
- **Response**: `200 OK` (`TokenResponse`: `access_token`, `token_type`, `role`)

#### 3. `POST /api/v1/auth/token` (OAuth2 Compatible Token Endpoint)
- **Auth Required**: No (Public)
- **Allowed Roles**: Any registered active user (used directly by Swagger UI Authorize modal)
- **Request Body**: `application/x-www-form-urlencoded` (`username`: email, `password`: password)
- **Response**: `200 OK` (`TokenResponse`: `access_token`, `token_type`, `role`)

#### 4. `GET /api/v1/auth/me`
- **Auth Required**: Yes (`OAuth2PasswordBearer`)
- **Allowed Roles**: Any active authenticated user
- **Request Parameters**: None
- **Response**: `200 OK` (`UserMeResponse`: `id`, `name`, `email`, `role`, `department`, `designation`, `is_active`)

---

### Group 2: Documents (`/documents`)

#### 4. `POST /api/v1/documents`
- **Auth Required**: Yes (`OAuth2PasswordBearer`)
- **Allowed Roles**: `TRAINER`, `ADMIN`
- **Request Body**: `multipart/form-data` (`file: UploadFile` - PDF, PPTX)
- **Response**: `201 Created` (`DocumentResponse`)

#### 5. `GET /api/v1/documents`
- **Auth Required**: Yes (`OAuth2PasswordBearer`)
- **Allowed Roles**: Authenticated (`TRAINER`, `SME`, `OFFICER`, `ADMIN`)
- **Query Parameters**: `skip: int = 0`, `limit: int = 100`
- **Response**: `200 OK` (`List[DocumentResponse]`)

#### 6. `GET /api/v1/documents/{document_id}`
- **Auth Required**: Yes (`OAuth2PasswordBearer`)
- **Allowed Roles**: Authenticated (`TRAINER`, `SME`, `OFFICER`, `ADMIN`)
- **Path Parameters**: `document_id: int`
- **Response**: `200 OK` (`DocumentDetailResponse` including `chunk_count`)

#### 7. `DELETE /api/v1/documents/{document_id}`
- **Auth Required**: Yes (`OAuth2PasswordBearer`)
- **Allowed Roles**: Original uploader or `ADMIN`
- **Path Parameters**: `document_id: int`
- **Response**: `200 OK` (`{"message": "Document deleted successfully", "id": int}`)

#### 8. `POST /api/v1/documents/search`
- **Auth Required**: Yes (`OAuth2PasswordBearer`)
- **Allowed Roles**: Authenticated (`TRAINER`, `SME`, `OFFICER`, `ADMIN`)
- **Request Body**: `application/json` (`DocumentSearchRequest`: `query`, `document_id`, `top_k`)
- **Response**: `200 OK` (`List[DocumentSearchResult]`)

---

### Group 3: Questions (`/questions`)

#### 9. `POST /api/v1/questions/generate`
- **Auth Required**: Yes (`OAuth2PasswordBearer`)
- **Allowed Roles**: `TRAINER`, `ADMIN`
- **Request Body**: `application/json` (`QuestionGenerateRequest`: `document_id`, `num_questions`, `difficulty`, `competency_id`)
- **Response**: `201 Created` (`List[QuestionResponse]`)

#### 10. `GET /api/v1/questions`
- **Auth Required**: Yes (`OAuth2PasswordBearer`)
- **Allowed Roles**: `TRAINER`, `SME`, `ADMIN` (OFFICER forbidden)
- **Query Parameters**: `document_id: Optional[int]`, `status: Optional[QuestionStatus]`, `competency_id: Optional[int]`, `difficulty: Optional[QuestionDifficulty]`, `skip: int = 0`, `limit: int = 50`
- **Response**: `200 OK` (`QuestionListResponse`: `total`, `items`)

#### 11. `GET /api/v1/questions/{question_id}`
- **Auth Required**: Yes (`OAuth2PasswordBearer`)
- **Allowed Roles**: `TRAINER`, `SME`, `ADMIN` (OFFICER forbidden)
- **Path Parameters**: `question_id: int`
- **Response**: `200 OK` (`QuestionResponse`)

---

### Group 4: System & Verification Endpoints

#### 12. `GET /`
- **Auth Required**: No | **Response**: `200 OK` (`{"app": "StatKarmayogi", ...}`)

#### 13. `GET /health`
- **Auth Required**: No | **Response**: `200 OK` (`{"status": "ok"}`)

#### 14. `GET /api/v1/test/authenticated`
- **Auth Required**: Yes (`OAuth2PasswordBearer`) | **Allowed Roles**: Any

#### 15. `GET /api/v1/test/trainer`
- **Auth Required**: Yes (`OAuth2PasswordBearer`) | **Allowed Roles**: `TRAINER`

#### 16. `GET /api/v1/test/sme`
- **Auth Required**: Yes (`OAuth2PasswordBearer`) | **Allowed Roles**: `SME`

#### 17. `GET /api/v1/test/officer`
- **Auth Required**: Yes (`OAuth2PasswordBearer`) | **Allowed Roles**: `OFFICER`

#### 18. `GET /api/v1/test/admin`
- **Auth Required**: Yes (`OAuth2PasswordBearer`) | **Allowed Roles**: `ADMIN`

---

## 7. Swagger Authentication & Authorize Flow Verification

1. **OpenAPI Security Scheme**: Configured as `OAuth2PasswordBearer` (`type: oauth2`, `flows.password.tokenUrl = /api/v1/auth/token`).
2. **Swagger UI Integration**:
   - The green **Authorize** button appears at the top-right of Swagger UI.
   - Lock icons appear on all protected routes.
3. **How to Authorize in Swagger UI**:
   - **Method A (Direct via Swagger Authorize modal — Recommended)**:
     1. Click the green **Authorize** button at the top-right of Swagger UI.
     2. In the OAuth2 password form modal, enter your registered email into the `username` field and your password into `password`.
     3. Click **Authorize**. Swagger UI submits `application/x-www-form-urlencoded` directly to `POST /api/v1/auth/token`, receives the JWT, and automatically attaches it to all subsequent requests.
   - **Method B (Via JSON /login endpoint)**:
     1. Expand `POST /api/v1/auth/login`.
     2. Click **Try it out**, enter credentials JSON `{"email": "...", "password": "..."}`, and click **Execute**.
     3. Copy the string value of `access_token` from the 200 response.
     4. Click **Authorize** at the top of Swagger UI, paste the token into the value box, and click **Authorize**.

---

## 8. Role-Based Access Control (RBAC) Verification Matrix

| Endpoint | TRAINER | SME | OFFICER | ADMIN | Actual Implementation | Status |
| :--- | :---: | :---: | :---: | :---: | :--- | :---: |
| **Document upload** (`POST /documents`) | **YES** | **NO** | **NO** | **YES** | `require_roles(RoleName.TRAINER, RoleName.ADMIN)` | **EXACT MATCH** |
| **Document list** (`GET /documents`) | **YES** | **YES** | **YES** | **YES** | `get_current_user` (Any authenticated user) | **EXACT MATCH** |
| **Document detail** (`GET /documents/{id}`) | **YES** | **YES** | **YES** | **YES** | `get_current_user` (Any authenticated user) | **EXACT MATCH** |
| **Document delete** (`DELETE /documents/{id}`) | **Uploader** | **NO** | **NO** | **YES** | Uploader check OR `RoleName.ADMIN` | **EXACT MATCH** |
| **Question generation** (`POST /questions/generate`) | **YES** | **NO** | **NO** | **YES** | `require_roles(RoleName.TRAINER, RoleName.ADMIN)` | **EXACT MATCH** |
| **Question list** (`GET /questions`) | **YES** | **YES** | **NO** | **YES** | `require_roles(RoleName.TRAINER, RoleName.SME, RoleName.ADMIN)` | **EXACT MATCH** |
| **Question detail** (`GET /questions/{id}`) | **YES** | **YES** | **NO** | **YES** | `require_roles(RoleName.TRAINER, RoleName.SME, RoleName.ADMIN)` | **EXACT MATCH** |

---

## 9. Manual Testing & Access Instructions

### Starting the Backend Server
```powershell
cd c:\SIH\backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Accessing Swagger UI
1. Open your browser and navigate to: `http://127.0.0.1:8000/docs`
2. Register development test accounts directly via `POST /api/v1/auth/register`:
   - **Trainer Account**:
     ```json
     {
       "name": "MoSPI Trainer",
       "email": "trainer@statkarmayogi.local",
       "password": "DevPassword123!",
       "role": "TRAINER",
       "department": "NSSTA",
       "designation": "Director of Training"
     }
     ```
   - **SME Account**:
     ```json
     {
       "name": "MoSPI SME",
       "email": "sme@statkarmayogi.local",
       "password": "DevPassword123!",
       "role": "SME",
       "department": "National Accounts Division",
       "designation": "Senior Statistician"
     }
     ```
   - **Officer Account**:
     ```json
     {
       "name": "MoSPI Officer",
       "email": "officer@statkarmayogi.local",
       "password": "DevPassword123!",
       "role": "OFFICER",
       "department": "FOD Regional Office",
       "designation": "Field Investigator"
     }
     ```
3. To test with an **Admin Account**:
   Since `ADMIN` registration is blocked from the public endpoint by design, existing admin accounts exist in the database (e.g. from tests), or you can promote any development user in pgAdmin with:
   ```sql
   UPDATE users SET role_id = (SELECT id FROM roles WHERE name = 'ADMIN') WHERE email = 'trainer@statkarmayogi.local';
   ```

---

## 10. Discrepancies, Issues & Findings

1. **`user_roles` Table**: The prompt requested verifying `user_roles`. In the authoritative schema, roles are modeled directly on the `users` table via `users.role_id` (foreign key to `roles.id`). This is by design (enforces single active role per officer) and functions as intended.
2. **No Schema Changes Needed**: All 16 tables, primary keys, foreign keys, unique constraints, and enums required for Phase 6 are already present in PostgreSQL.

---

## 11. Final System Status

```text
==================================================
SYSTEM STATUS:
READY FOR PHASE 6
==================================================
```
The database, ChromaDB vector store, authentication pipeline, document ingestion, and MCQ generation systems are completely verified, synchronized, and operational.
