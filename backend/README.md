# StatKarmayogi — Backend

**Smart India Hackathon 2026**
- **Problem Statement ID**: SIH26101
- **Organization**: Ministry of Statistics and Programme Implementation (MoSPI)
- **Theme**: Smart Education

---

## 1. Project Purpose

**StatKarmayogi** is an AI-enabled competency assessment and adaptive learning platform designed for the Ministry of Statistics and Programme Implementation (MoSPI). 

The platform implements an evidence-based closed learning loop:
$$\text{Assess} \longrightarrow \text{Gap} \longrightarrow \text{Learn} \longrightarrow \text{Reassess}$$

Key capabilities include:
- Grounded AI MCQ generation from official MoSPI manuals (PDF/PPT).
- Human-in-the-loop Subject Matter Expert (SME) quality gate.
- Deterministic competency evaluation and topic-level skill gap identification.
- Personalized course recommendations mapped to real public iGOT Karmayogi courses via a mock REST adapter.
- Reassessment tracking to measure skill progression.

---

## 2. Current Architecture & Stack

### Backend Stack
- **Framework**: FastAPI (Python 3.14+)
- **Database**: PostgreSQL with synchronous SQLAlchemy 2.x ORM
- **DB Driver**: `psycopg` (psycopg 3 binary: `postgresql+psycopg://...`)
- **Database Migrations**: Alembic
- **Configuration & Validation**: Pydantic v2 & Pydantic Settings
- **Testing**: Pytest & HTTPX (FastAPI TestClient)
- **CORS Support**: Pre-configured for frontend integration (Streamlit on port 8501, React, etc.)

---

## 3. Directory Structure

```text
backend/
├── app/
│   ├── __init__.py           # Application package init
│   ├── main.py              # FastAPI entrypoint with CORS and health endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py         # Pydantic Settings environment configuration
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py           # SQLAlchemy 2.x DeclarativeBase
│   │   └── session.py        # Engine (pool_pre_ping=True), SessionLocal, get_db dependency
│   ├── models/               # SQLAlchemy models (Phase 2)
│   │   └── __init__.py
│   ├── schemas/              # Pydantic schemas (Phase 2+)
│   │   └── __init__.py
│   ├── routers/              # API route handlers (Phase 3+)
│   │   └── __init__.py
│   ├── services/             # Business logic services
│   │   └── __init__.py
│   ├── ai/                   # RAG, ChromaDB, and Mistral LLM pipeline (Phase 4-5)
│   │   └── __init__.py
│   └── integrations/         # Mock iGOT REST adapter (Phase 10)
│       └── __init__.py
├── alembic/
│   ├── env.py                # Alembic environment connected to app config and Base.metadata
│   ├── script.py.mako        # Migration script template
│   └── versions/             # Migration version scripts
├── tests/
│   ├── __init__.py
│   └── test_health.py        # Health, root endpoint, and foundation unit tests
├── alembic.ini               # Alembic configuration
├── .env.example              # Environment variables template
├── .gitignore                # Git ignore rules
├── requirements.txt          # Minimal Phase 1 dependencies
└── README.md                 # Backend documentation
```

---

## 4. Environment Setup

Copy `.env.example` to create your local `.env` file:

```bash
cp .env.example .env
```

### Configuration Variables (`.env`)

| Variable | Description | Default |
| :--- | :--- | :--- |
| `DATABASE_URL` | PostgreSQL connection URL using psycopg 3 | `postgresql+psycopg://postgres:password@localhost:5432/statkarmayogi_db` |
| `APP_NAME` | Name of the application | `StatKarmayogi` |
| `APP_ENV` | Application environment (`development` / `production`) | `development` |
| `DEBUG` | Enable debug mode and SQL query logging | `true` |
| `API_V1_PREFIX` | Prefix for version 1 API endpoints | `/api/v1` |
| `CORS_ORIGINS` | Allowed CORS origins for frontend integration | `["http://localhost:8501", ...]` |

---

## 5. PostgreSQL Database Setup

Ensure PostgreSQL is installed and running. Create the application database:

```sql
CREATE DATABASE statkarmayogi_db;
```

Update `DATABASE_URL` in `.env` with your PostgreSQL username, password, host, and port.

---

## 6. Installation

Install dependencies using pip:

```bash
pip install -r requirements.txt
```

---

## 7. Running the FastAPI Application

Start the development server with Uvicorn:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Once running:
- **Interactive API Documentation (Swagger UI)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Alternative Documentation (ReDoc)**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Root Endpoint**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Health Check Endpoint**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### Health Check Response
```json
{
  "status": "ok"
}
```

---

## 8. Database Migrations (Alembic)

Alembic is configured to read model metadata directly from `app.db.base.Base.metadata` and the database URL from `app.core.config.settings.DATABASE_URL`.

Common commands:

```bash
# Check current migration status
alembic current

# Check target migration heads
alembic heads

# Generate a new migration (Phase 2+)
alembic revision --autogenerate -m "create initial models"

# Apply migrations
alembic upgrade head
```

---

## 9. Running Tests

Run the test suite with pytest:

```bash
pytest
```

---

---

---

## 10. Database Seeding

Seed the initial 4 system roles (`TRAINER`, `SME`, `OFFICER`, `ADMIN`):

```bash
python -m app.db.seed
```

This seed operation is idempotent and safe to execute multiple times.

---

## 11. Authentication & Authorization (Phase 3)

StatKarmayogi implements JWT-based authentication combined with Argon2 password hashing and authoritative database role resolution.

### Core Architectural Rules
> [!IMPORTANT]
> **ROLE IS SELECTED DURING REGISTRATION.**
> - Supported registration roles: `TRAINER`, `SME`, `OFFICER`.
> - `ADMIN` accounts cannot be self-registered publicly; they require controlled administrator creation.
>
> **ROLE IS NOT SELECTED DURING LOGIN.**
> - Login requests contain **only email and password**.
> - The backend retrieves the stored role from `users.role_id` and binds it to the signed JWT.

### Endpoints
- **Register**: `POST /api/v1/auth/register`
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
- **Login**: `POST /api/v1/auth/login`
  ```json
  {
    "email": "priya.sharma@mospi.gov.in",
    "password": "StrongPassword123!"
  }
  ```
- **Current User Profile**: `GET /api/v1/auth/me`  
  Header: `Authorization: Bearer <token>`
- **Authorization Verification Test Endpoints**:
  - `GET /api/v1/test/authenticated` (Any active user with valid JWT)
  - `GET /api/v1/test/trainer` (Requires `TRAINER` role)
  - `GET /api/v1/test/sme` (Requires `SME` role)
  - `GET /api/v1/test/officer` (Requires `OFFICER` role)
  - `GET /api/v1/test/admin` (Requires `ADMIN` role)

### Security & JWT Configuration
Set in `.env`:
```bash
JWT_SECRET_KEY=e83a7c6f09b514b8a6e927c3d71e2f4a5c68b91a2d3e4f5a6b7c8d9e0f1a2b3c
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```
- `password_hash` is computed with Argon2id and is **never** returned in any API response or logged.
- Inactive users are rejected with `HTTP 403 Forbidden`.
- Unauthorized roles are rejected with `HTTP 403 Forbidden`.

---

---

## 12. Document Ingestion & Vector Pipeline (Phase 4)

StatKarmayogi implements the authoritative RAG document ingestion pipeline specified in the MoSPI project documentation.

### Workflow Architecture
```
Authenticated User (TRAINER / ADMIN)
        ↓
POST /api/v1/documents (multipart/form-data)
        ↓
Validate file extension (.pdf, .pptx) & payload size (<= MAX_UPLOAD_SIZE_MB)
        ↓
Sanitize filename & stream to storage/documents/{uuid}_{filename}
        ↓
Create documents record (status = UPLOADED)
        ↓
Transition status to PROCESSING
        ↓
LangChain Document Loading:
  • PDF  → PyPDFLoader (page-level metadata preserved)
  • PPTX → python-pptx non-AI parser → LangChain Documents (slide-level metadata preserved)
        ↓
Structure-Preserving Recursive Text Splitting:
  • LangChain RecursiveCharacterTextSplitter (CHUNK_SIZE=1000, CHUNK_OVERLAP=150)
  • Deterministic SHA-256 content_hash computed per chunk
        ↓
Mistral AI Vector Embeddings:
  • MistralAIEmbeddings (model: mistral-embed)
  • Dynamic vector dimensionality
        ↓
Persistent ChromaDB Vector Indexing:
  • Collection: statkarmayogi_chunks (persistent at storage/chroma)
  • Deterministic ID: doc_{document_id}_chunk_{chunk_index}_{content_hash[:16]}
  • Metadata: document_id, chunk_index, page_number, content_hash, filename
        ↓
PostgreSQL Chunk Traceability:
  • document_chunks rows populated with matching chroma_id
        ↓
Transition document status to PROCESSED
```

### Two-System Consistency Strategy (Failure Compensation)
PostgreSQL and ChromaDB do not share a distributed transaction. To prevent inconsistent states:
1. **Embedding Failure**: Document transitions to `FAILED`; zero vectors added to ChromaDB; zero chunks in PostgreSQL.
2. **ChromaDB Failure**: Document transitions to `FAILED`; no `chroma_id` values written to PostgreSQL.
3. **PostgreSQL Chunk Failure (Compensation)**: If database persistence fails after ChromaDB vector insertion, the added ChromaDB vectors are immediately purged via `VectorStoreService.delete_by_ids(chroma_ids)`, ensuring no orphaned vectors remain.

### Endpoints
- **Upload Document**: `POST /api/v1/documents`
  - Permitted Roles: `TRAINER`, `ADMIN`
  - Returns `201 Created` with `DocumentResponse`
- **List Documents**: `GET /api/v1/documents`
  - Permitted Roles: Authenticated users (`TRAINER`, `SME`, `OFFICER`, `ADMIN`)
  - Returns `200 OK` with `List[DocumentResponse]`
- **Document Detail**: `GET /api/v1/documents/{document_id}`
  - Returns `200 OK` with `DocumentDetailResponse` (including `chunk_count`)
- **Semantic Vector Search**: `POST /api/v1/documents/search`
  - Body: `{"query": "string", "document_id": optional_int, "top_k": 5}`
  - Returns `200 OK` with matching chunk texts, metadata, and similarity distances
- **Delete Document**: `DELETE /api/v1/documents/{document_id}`
  - Permitted Roles: Original uploader or `ADMIN`
  - Action: Removes ChromaDB vectors, cascades deletion of PostgreSQL records, unlinks physical file

### Environment Configuration
```bash
# Document Upload
UPLOAD_DIR=storage/documents
MAX_UPLOAD_SIZE_MB=20
CHUNK_SIZE=1000
CHUNK_OVERLAP=150

# Mistral AI Embeddings
MISTRAL_API_KEY=your_mistral_api_key_here
MISTRAL_EMBEDDING_MODEL=mistral-embed

# ChromaDB Vector Store
CHROMA_PERSIST_DIRECTORY=storage/chroma
CHROMA_COLLECTION_NAME=statkarmayogi_chunks
```

---

## 13. MCQ Generation & Prompt Engineering (Phase 5)

StatKarmayogi implements Retrieval-Augmented Generation (RAG) for automated MCQ generation from MoSPI training documents using Mistral AI (`ChatMistralAI`).

### Generation Architecture & Grounding Pipeline
```
Authenticated User (TRAINER / ADMIN)
        ↓
POST /api/v1/questions/generate
        ↓
Validate Document Status (Must be PROCESSED)
        ↓
Load Competency Constraints from PostgreSQL (if competency_id provided)
        ↓
Vector Retrieval via ChromaDB (Primary Retrieval Mechanism):
  • Query vector generated via Mistral Embeddings
  • ChromaDB similarity search with where={"document_id": document_id}
  • Relational metadata cross-referenced with PostgreSQL document_chunks
        ↓
Prompt Engineering with Strict Grounding:
  • Context chunks marked with [CHUNK ID: {id}, PAGE: {page}]
  • Strict grounding rules: rely SOLELY on provided facts, no external speculation
  • 4 distinct options, exactly one correct, educational explanation
        ↓
Structured LLM Invocation:
  • ChatMistralAI(model=MISTRAL_LLM_MODEL, temperature=MISTRAL_TEMPERATURE)
  • with_structured_output(MCQGenerationBatch)
        ↓
Quality & Grounding Verification:
  • 4 distinct non-empty options validated
  • Valid correct_option ('A', 'B', 'C', or 'D')
  • Explicit source chunk attribution: LLM-returned source_chunk_id MUST exist in retrieved context
  • Intra-batch question deduplication
        ↓
Atomic Single-Transaction Persistence:
  • Questions inserted with status = PENDING_REVIEW
  • documents.generation_count incremented in the same transaction
```

### Endpoints
- **Generate MCQs**: `POST /api/v1/questions/generate`
  - Roles: `TRAINER`, `ADMIN`
  - Payload:
    ```json
    {
      "document_id": 1,
      "num_questions": 5,
      "difficulty": "MEDIUM",
      "competency_id": 2
    }
    ```
  - Returns `201 Created` with `List[QuestionResponse]`
- **List Questions**: `GET /api/v1/questions`
  - Roles: `TRAINER`, `SME`, `ADMIN`
  - Filters: `document_id`, `status`, `competency_id`, `difficulty`, `skip`, `limit`
  - Returns `200 OK` with `QuestionListResponse` (`total`, `items`)
- **Question Detail**: `GET /api/v1/questions/{question_id}`
  - Roles: `TRAINER`, `SME`, `ADMIN`
  - Returns `200 OK` with full question metadata, options, explanation, source page, and source chunk ID

### Environment Configuration
```bash
# Mistral AI LLM & MCQ Generation
MISTRAL_LLM_MODEL=mistral-large-latest
MISTRAL_TEMPERATURE=0.2
DEFAULT_MCQ_VOLUME=5
MAX_MCQ_VOLUME=20
```

---

## 14. Human-in-the-Loop SME Question Review (Phase 6)

StatKarmayogi implements a rigorous Subject Matter Expert (SME) validation queue. Generated questions remain in `PENDING_REVIEW` status until an authorized MoSPI Subject Matter Expert or Administrator evaluates them.

### Review Workflow & Lifecycle
```
PENDING_REVIEW Question in Review Queue (GET /api/v1/questions?status=PENDING_REVIEW)
        ↓
POST /api/v1/questions/{question_id}/review
        ↓
Role Verification: Only SME or ADMIN permitted (TRAINER and OFFICER rejected with 403)
        ↓
Lifecycle Validation: Strictly rejects questions not in PENDING_REVIEW (400 Bad Request)
        ↓
Atomic Single-Transaction Execution:
  • Creates QuestionReview audit entry (reviewer_id, action, comment, timestamp)
  • Updates question.status to APPROVED or REJECTED
  • If any error occurs, performs db.rollback()
        ↓
Auditable Review Persisted: Question source chunk provenance preserved intact
```

### Endpoints
- **Review Question**: `POST /api/v1/questions/{question_id}/review`
  - Permitted Roles: `SME`, `ADMIN`
  - Payload:
    ```json
    {
      "action": "APPROVE",
      "comment": "Accurate calculation logic and faithful citation of ASI guidelines."
    }
    ```
  - Returns `200 OK` with `QuestionReviewResponse` (review audit details and updated question entity)
- **Review Queue**: `GET /api/v1/questions?status=PENDING_REVIEW`
  - Permitted Roles: `TRAINER`, `SME`, `ADMIN`
  - Returns `200 OK` with paginated list of questions awaiting expert review

---

---

## 15. Officer Assessment, Deterministic Scoring & Competency Gap Analysis (Phase 7)

StatKarmayogi implements the officer assessment and deterministic competency evaluation pipeline. Assessments only draw from SME-approved, competency-tagged MCQs (`QuestionStatus.APPROVED`, `competency_id IS NOT NULL`).

### Assessment Workflow Architecture
```
Officer / Admin creates Assessment
        ↓
POST /api/v1/assessments
  • Deterministic Question Selection (ORDER BY questions.id ASC)
  • Filters: competency_id (optional), document_id (optional)
  • Volume: 1–50 questions (default: 10)
  • Persists Assessment (status: IN_PROGRESS) + AssessmentQuestions
        ↓
Officer Views Assessment
GET /api/v1/assessments/{id}
  • Strict Exam Security: correct_option, explanation, source_page, source_chunk_id MASKED (null)
        ↓
Officer Submits All Answers
POST /api/v1/assessments/{id}/submit
  • Validates complete submission (all assigned questions answered, no duplicates/unassigned)
  • Zero-AI Deterministic Scoring: exact answer matching (is_correct)
  • Computes overall percentage score
  • Aggregates competency-wise scores (questions_answered, questions_correct, score_percentage)
  • Determines Proficiency Level:
      ADVANCED (>= 80%), PROFICIENT (>= 65%), DEVELOPING (>= 50%), BEGINNER (< 50%)
  • Identifies Skill Gaps:
      HIGH (< 50%), MEDIUM (< 65%), LOW (< 80%)
  • Single Atomic Database Transaction:
      answers + competency_results + skill_gaps + assessment.status = COMPLETED
        ↓
Officer / Trainer / Admin Views Detailed Result
GET /api/v1/assessments/{id}/result
  • Unmasks full evaluation: selected_option, correct_option, is_correct, explanation, citations
```

> [!NOTE]
> Proficiency and skill gap percentage thresholds (`ADVANCED: 80%`, `PROFICIENT: 65%`, `DEVELOPING: 50%`) are configurable prototype calibration values defined in `app/core/config.py` and are not official MoSPI standards.

### Endpoints
- **Create Assessment**: `POST /api/v1/assessments`
  - Permitted Roles: `OFFICER`, `ADMIN`
  - Payload:
    ```json
    {
      "title": "National Accounts & ASI Competency Evaluation",
      "competency_id": 1,
      "document_id": null,
      "num_questions": 10
    }
    ```
  - Returns `201 Created` with `AssessmentDetailResponse` (safe masked questions)
- **List Assessments**: `GET /api/v1/assessments`
  - Permitted Roles: `OFFICER` (own assessments), `TRAINER` (all assessments), `ADMIN` (all assessments). `SME` receives `403 Forbidden`.
  - Filters: `status`, `skip`, `limit`
  - Returns `200 OK` with `AssessmentListResponse`
- **Get Assessment (Exam Screen)**: `GET /api/v1/assessments/{assessment_id}`
  - Permitted Roles: Owner `OFFICER`, `TRAINER`, `ADMIN`
  - Returns `200 OK` with `AssessmentDetailResponse` (safe masked questions while `IN_PROGRESS`)
- **Submit Assessment**: `POST /api/v1/assessments/{assessment_id}/submit`
  - Permitted Roles: Assessment Owner (`OFFICER`) or `ADMIN`
  - Payload:
    ```json
    {
      "answers": [
        {"question_id": 1, "selected_option": "B"},
        {"question_id": 2, "selected_option": "A"}
      ]
    }
    ```
  - Returns `200 OK` with `AssessmentResultResponse` (score, competency results, skill gaps)
- **Get Assessment Result**: `GET /api/v1/assessments/{assessment_id}/result`
  - Permitted Roles: Owner `OFFICER`, `TRAINER`, `ADMIN`
  - Requires status `COMPLETED` (returns `400 Bad Request` if `IN_PROGRESS`)
  - Returns `200 OK` with `AssessmentResultResponse` and unmasked `questions` review

### Course Catalogue & Recommendations Endpoints (Phase 8)

- **List Courses**: `GET /api/v1/courses`
  - Permitted Roles: Authenticated users (`OFFICER`, `TRAINER`, `ADMIN`, `SME`)
  - Query Filters: `query`, `competency_id`, `difficulty`, `language`, `skip`, `limit`
  - Returns `200 OK` with `CourseListResponse`
- **Get Course Detail**: `GET /api/v1/courses/{course_id}`
  - Permitted Roles: Authenticated users (`OFFICER`, `TRAINER`, `ADMIN`, `SME`)
  - Returns `200 OK` with `CourseDetailResponse` including linked competency mappings and relevance scores
- **Generate Recommendations**: `POST /api/v1/assessments/{assessment_id}/recommendations`
  - Permitted Roles: Owner `OFFICER`, `ADMIN` (TRAINER and SME receive `403 Forbidden`)
  - Deterministically generates course recommendations from identified skill gaps
  - Returns `200 OK` with `List[RecommendationResponse]`
- **List Assessment Recommendations**: `GET /api/v1/assessments/{assessment_id}/recommendations`
  - Permitted Roles: Owner `OFFICER`, `TRAINER`, `ADMIN` (SME receives `403 Forbidden`)
  - Returns `200 OK` with `List[RecommendationResponse]`
- **List Recommendations (Cross-Assessment)**: `GET /api/v1/recommendations`
  - Permitted Roles: `OFFICER` (own only), `TRAINER` (all), `ADMIN` (all)
  - Query Filters: `assessment_id`, `status`, `skip`, `limit`
  - Returns `200 OK` with `RecommendationListResponse`
- **Get Recommendation**: `GET /api/v1/recommendations/{recommendation_id}`
  - Permitted Roles: Owner `OFFICER`, `TRAINER`, `ADMIN`
  - Returns `200 OK` with `RecommendationResponse`
- **Update Recommendation Status**: `PATCH /api/v1/recommendations/{recommendation_id}/status`
  - Permitted Roles: Owner `OFFICER`, `ADMIN`
  - Enforces status state machine (`RECOMMENDED` -> `STARTED` -> `COMPLETED` or `RECOMMENDED` -> `DISMISSED`)
  - Terminal states (`COMPLETED`, `DISMISSED`) reject further updates (`400 Bad Request`)
  - Returns `200 OK` with updated `RecommendationResponse`

---

## 16. Running Tests

Run the full automated test suite (foundation, database schema, authentication, LangChain, Mistral Embeddings, ChromaDB, RAG MCQ generation, SME review workflow, Phase 7 assessment & scoring, and Phase 8 recommendations):

```bash
python -m pytest -v
```

> [!NOTE]
> All 150 automated tests execute with zero external API calls (mock embeddings, deterministic scoring, and local mock adapter), completing in ~8 seconds without consuming API credits or altering production data.

---

## 17. Current Development Phase

- **Current Status**: **Phase 8 Completed & Verified** (iGOT Learning Pathways & Course Recommendations).
  - Zero database schema modifications (existing 16-table PostgreSQL schema strictly preserved).
  - 100% deterministic matching: $\text{match\_score} = \operatorname{round}(\text{relevance\_score} \times \text{gap\_multiplier} \times 100, 2)$.
  - Multipliers & Priority: HIGH (1.00, Priority 1), MEDIUM (0.85, Priority 2), LOW (0.70, Priority 3).
  - Deterministic tie-breaking: `priority ASC` -> `match_score DESC` -> `relevance_score DESC` -> `course_id ASC`.
  - Recommendation limits: max 2 per gap; single authoritative active recommendation cap of 6 (`MAX_TOTAL_ACTIVE_RECOMMENDATIONS = 6`).
  - Regeneration idempotency: preserves `STARTED`, `COMPLETED`, and `DISMISSED` records; total rows in database can legitimately exceed 6 with history.
  - State machine: `RECOMMENDED` -> `STARTED` -> `COMPLETED` (terminal); `RECOMMENDED` -> `DISMISSED` (terminal).
  - Safe transaction boundaries: assessment submission commits diagnostic results first; recommendation generation runs in secondary isolated block without risking assessment rollback.
  - Zero dead or fake URLs: course URLs point to implemented routes or are null.
  - **150/150 passing automated tests** across all 8 phases (25 Phase 8 tests).
- **Next Phase**: **Phase 9 — Officer Reassessment & Closed-Loop Learning Progression** (Post-learning quiz to measure score improvement and competency gap closure).

