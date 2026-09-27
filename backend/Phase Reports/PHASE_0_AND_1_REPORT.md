# StatKarmayogi — Project Report (Phase 0 & Phase 1)

**Smart India Hackathon 2026**  
- **Problem Statement ID**: SIH26101  
- **Problem Statement Title**: StatKarmayogi: AI-Driven Competency Assessment & Adaptive iGOT Learning Pathway for MoSPI  
- **Organization**: Ministry of Statistics and Programme Implementation (MoSPI)  
- **Team**: Zero Risk (Team ID: 64)  
- **Current Milestone**: Phase 0 Complete | Phase 1 Complete  

---

## Part 1: Phase 0 — Understand the Project

Extracted directly from project reference materials:
- `SIH-2026 Zero Risk 64.pptx`
- `StatKarmayogi_Final_Backend_Schema_and_Development_Flow.pdf`

---

### 1. Problem Statement
- **Problem Statement ID**: SIH26101
- **Title**: StatKarmayogi: AI-Driven Competency Assessment & Adaptive iGOT Learning Pathway for MoSPI
- **Context & Need**: MoSPI's internal 2025 NSSTA Statistical Training Needs Assessment (STA) Survey revealed critical competency gaps among Indian Statistical Service (ISS) officers—specifically in AI, big data analytics, macroeconomic statistics, and cross-functional skills.
- **Current Bottlenecks**:
  - Capacity-building needs in civil services are currently self-declared and static rather than objectively measured.
  - Manual creation and evaluation of multi-level MCQs from voluminous official statistical manuals is labor-intensive and inconsistent.
  - There is a complete lack of automated, closed-loop links between topic-level competency deficits and the 17M+ user iGOT Karmayogi learning ecosystem.

---

### 2. Project Objective
To build an AI-enabled competency assessment and adaptive learning prototype for MoSPI that implements an evidence-based closed learning loop:

$$\text{Assess} \longrightarrow \text{Gap} \longrightarrow \text{Learn} \longrightarrow \text{Reassess}$$

Core objectives:
1. **Grounded Question Generation**: Ingest official MoSPI manuals (PDF/PPT) and generate difficulty- and competency-tagged MCQs strictly grounded in source material via RAG to eliminate hallucinations.
2. **Human-in-the-Loop Quality Gate**: Subject Matter Experts (SMEs) validate, edit, approve, or reject generated questions before they enter the assessment question bank.
3. **Objective Competency Diagnosis**: Compute deterministic competency proficiency scores and identify granular skill gaps for officers.
4. **Targeted iGOT Course Routing**: Recommend publicly accessible iGOT courses mapped to weak competencies via an API-ready mock REST adapter.
5. **Impact Measurement (Reassessment)**: Facilitate post-learning reassessments to measure proficiency gains and close the learning loop.

---

### 3. Required Features
- **Role-at-Registration Authentication**: User selects role during account creation (`TRAINER`, `SME`, `OFFICER`, `ADMIN`). Direct login without a role selector; backend reads stored role and issues role-based JWT.
- **Source Document Processing**: Upload PDF/PPT manuals, extract text, split into semantic chunks, and track source chunk metadata.
- **RAG & Vector Retrieval**: Mistral embeddings vectorization and ChromaDB vector storage with PostgreSQL chunk-to-document traceability.
- **Grounded AI MCQ Generation**: Mistral LLM generates candidate MCQs in structured JSON format tagged with competency, difficulty, explanation, source page, and source chunk ID, with trainer-controlled generation volume.
- **SME Validation Portal**: Dedicated review queue allowing SMEs to inspect source grounding, edit question components, and approve or reject questions into the assessment pool.
- **Deterministic Assessment Engine**: Assessment creation, question assignment, timed/managed test taking, answer submission, and deterministic evaluation.
- **Competency & Skill-Gap Engine**: Answer aggregation by competency, proficiency classification, and identification of deficient competencies.
- **Sample Public iGOT Catalogue**: Local catalogue of real publicly accessible iGOT courses pre-mapped to statistical competencies with relevance scoring.
- **Explainable Course Recommendations**: Algorithmic course ranking by priority and match score, with human-readable explanations explaining why each course was suggested.
- **Mock iGOT REST Adapter**: Simulates standard iGOT course catalogue and enrollment REST API contracts without requiring unauthorized production API access.
- **Reassessment Engine**: Comparative assessment engine evaluating pre- and post-learning performance.
- **Visual Analytics**: Interactive Plotly radar charts (skill profiles) and bar charts (competency breakdowns) for the frontend dashboard.

---

### 4. Target Users
1. **Government Officials / Learners (ISS Officers & MoSPI Personnel)**: Take diagnostic tests, review personal skill gaps, follow targeted learning pathways, and track growth.
2. **MoSPI Trainers & Course Coordinators**: Ingest manuals, configure generation volume, and trigger question generation.
3. **Subject Matter Experts (SMEs)**: Review and certify generated questions for domain, factual, and pedagogical correctness.
4. **MoSPI Leadership & HR Administrators**: Analyze aggregated department-wide skill gap heatmaps for strategic workforce planning.

---

### 5. User Roles
- **`TRAINER`**: Uploads learning material (PDF/PPT), sets MCQ generation volume, triggers generation, and views generated question lists.
- **`SME`**: Reviews, edits, approves, or rejects generated MCQs in the review queue.
- **`OFFICER`**: Takes diagnostic assessments, reviews scores and skill gaps, receives course recommendations, learns on iGOT, and takes reassessments.
- **`ADMIN`**: Manages users, accounts, competency framework taxonomies, course catalogues, and overall system data.

---

### 6. Role-Specific Workflows
- **Trainer Workflow**:
  $$\text{Register (Trainer)} \rightarrow \text{Login} \rightarrow \text{Upload Manual (PDF/PPT)} \rightarrow \text{Set MCQ Volume} \rightarrow \text{Trigger AI Generation} \rightarrow \text{Track Question Status}$$
- **SME Workflow**:
  $$\text{Register (SME)} \rightarrow \text{Login} \rightarrow \text{Open Review Queue} \rightarrow \text{Inspect MCQ \& Source Chunk Traceability} \rightarrow \text{Edit / Approve / Reject} \rightarrow \text{MCQs Enter Assessment Bank}$$
- **Officer Workflow**:
  $$\text{Register (Officer)} \rightarrow \text{Login} \rightarrow \text{Start Assessment} \rightarrow \text{Submit Answers} \rightarrow \text{View Deterministic Proficiency \& Gap Visuals} \rightarrow \text{Receive iGOT Recommendations} \rightarrow \text{Learn} \rightarrow \text{Reassess}$$
- **Admin Workflow**:
  $$\text{Register / Assign Admin} \rightarrow \text{Login} \rightarrow \text{Manage Users \& Permissions} \rightarrow \text{Maintain Competency Taxonomies} \rightarrow \text{Maintain Course Catalogues}$$

---

### 7. Required Technology / Frameworks
| Layer | Technology | Responsibility |
| :--- | :--- | :--- |
| **Frontend** | Streamlit + Plotly | User interfaces (Trainer console, SME queue, Officer quiz, Radar/Bar charts) |
| **Backend API** | FastAPI (Python 3.14+) | High-performance REST API layer, CORS middleware |
| **Database** | PostgreSQL | Relational storage for users, questions, assessments, gaps, courses |
| **ORM & Migrations** | SQLAlchemy 2.x + Alembic | Modern synchronous ORM (`DeclarativeBase`, `SessionLocal`), schema versioning |
| **DB Driver** | `psycopg` (psycopg 3 binary) | Recommended PostgreSQL 3.x driver (`postgresql+psycopg://...`) |
| **Configuration** | Pydantic v2 + Pydantic Settings | Typed environment variable loading and validation |
| **Document/RAG Ingestion** | LangChain + `PyPDFLoader` | Document text extraction and semantic chunking |
| **AI / Embeddings / LLM** | Mistral Embeddings + Mistral LLM | Vectorization and structured JSON MCQ generation |
| **Vector Store** | ChromaDB | Local vector indexing and semantic similarity search |
| **Integration Layer** | Mock iGOT REST Adapter | Exposes sample public iGOT course catalogue and enrollment contracts |
| **Testing** | Pytest + HTTPX | Automated unit and API testing (`TestClient`) |

---

### 8. AI/RAG Architecture
1. **Extraction**: `PyPDFLoader` parses uploaded PDF/PPT manuals into raw text.
2. **Chunking**: LangChain semantic text splitters divide text into contextual chunks.
3. **Dual Persistence**:
   - Vectors are stored in **ChromaDB**.
   - Chunk traceability metadata (`chunk_index`, `page_number`, `content_hash`, `chroma_id`) is stored in PostgreSQL `document_chunks`.
4. **Retrieval**: Semantic retriever queries ChromaDB for relevant source context.
5. **Structured LLM Generation**: Mistral LLM is prompted with context and outputs strict JSON conforming to schema.
6. **Backend Validation**: Pydantic validates schema before database persistence (`PENDING_REVIEW`).
7. **Traceability**: Every question retains `source_page` and `source_chunk_id` for auditable proof of grounding.

---

### 9. MCQ Generation Workflow
- Trainer uploads source document and inputs generation parameters (target volume).
- Backend queries ChromaDB for relevant chunks.
- Mistral LLM generates candidate MCQs conforming to JSON schema: `question_text`, `options` (A–D), `correct_option`, `difficulty`, `explanation`, `competency_id`, `source_page`, and `source_chunk_id`.
- Backend validates JSON structure with Pydantic.
- Questions are stored in PostgreSQL `questions` table with initial status `PENDING_REVIEW`.

---

### 10. SME Validation Workflow
- SME accesses the review queue of unreviewed questions.
- SME views question text, options, answer, explanation, and grounds against source document chunks.
- SME can modify any field (text, options, explanation, difficulty, competency).
- SME records an action (`APPROVE` or `REJECT`) with optional comments.
- Review event is logged in `question_reviews` (auditing `question_id`, `reviewer_id`, `action`, `comment`, `created_at`).
- Approved questions transition to status `APPROVED` and enter the assessment pool.

---

### 11. Officer Assessment Workflow
- Backend instantiates an assessment record in `assessments` for `officer_id`.
- Approved questions are selected and mapped via `assessment_questions`.
- Officer answers questions in the UI.
- Responses are saved in `answers` with evaluation of correctness (`is_correct`).
- System computes deterministic scores (`total_questions`, `total_correct`, `score_percentage`) and sets completion timestamp.

---

### 12. Competency-Gap Identification
- Backend groups officer responses by `competency_id`.
- Computes `questions_attempted`, `questions_correct`, `score_percentage`, and assigns `proficiency_level` in `competency_results`.
- Competencies scoring below mastery threshold are inserted into `skill_gaps` with severity `gap_level` (High, Medium, Low).
- Aggregated gap metrics are exported to Plotly radar and bar charts for immediate visual feedback.

---

### 13. iGOT Learning / Recommendation Workflow
- Real publicly accessible iGOT courses are catalogued in `courses` and mapped to competencies in `course_competencies` with relevance scores.
- Recommendation engine matches identified `skill_gaps` against course mappings.
- Courses addressing detected gaps are prioritized and scored (`priority`, `match_score`).
- Recommendations are saved in `recommendations` with human-readable rationale.
- Recommendations and course metadata are served via the Mock iGOT REST adapter.

---

### 14. Reassessment Workflow
- Officer reviews recommendations and completes recommended learning modules on iGOT.
- Officer initiates a reassessment covering the same or targeted competencies.
- Backend scores the reassessment and calculates new competency proficiency levels.
- System performs before-and-after comparative analysis to quantitatively verify skill gap closure.

---

### 15. Database Requirements
15 relational entities in PostgreSQL managed via SQLAlchemy 2.x and Alembic:
1. `roles`: System roles (`TRAINER`, `SME`, `OFFICER`, `ADMIN`).
2. `users`: Identity, hashed password, role foreign key, department, designation, status, timestamps.
3. `competencies`: Competency framework codes, names, descriptions, categories.
4. `documents`: Uploaded manuals, file paths, processing status, generation count, timestamps.
5. `document_chunks`: Chunk index, page number, content hash, ChromaDB vector ID for source traceability.
6. `questions`: MCQs, options A–D, correct answer, difficulty, explanation, source page/chunk, status.
7. `question_reviews`: SME review audit trail (action, comments, reviewer ID, timestamp).
8. `assessments`: Officer assessment instances, scores, start and completion timestamps.
9. `assessment_questions`: Mapping and ordering of questions assigned to an assessment.
10. `answers`: Officer choices and evaluation correctness.
11. `competency_results`: Granular assessment scores and proficiency levels per competency.
12. `skill_gaps`: Identified competency deficiencies and gap severity levels.
13. `courses`: Public iGOT course catalogue metadata (course ID, title, provider, duration, URL).
14. `course_competencies`: Relational mapping of courses to competencies with relevance scores.
15. `recommendations`: Prioritized, explainable course recommendations linked to officers and assessments.

---

### 16. Backend Requirements
- **Framework**: FastAPI modular structure (`app/core`, `app/db`, `app/models`, `app/schemas`, `app/routers`, `app/services`, `app/ai`, `app/integrations`).
- **Database Engine**: Synchronous SQLAlchemy 2.x engine with `pool_pre_ping=True`, `SessionLocal`, and `get_db` dependency.
- **Environment Management**: Typed Pydantic Settings reading from `.env`.
- **Migrations**: Alembic linked to application settings and `Base.metadata`.
- **CORS Middleware**: Configured to support frontend integration on standard development ports.
- **Endpoints**: Standard `/` metadata and `/health` monitoring (`{"status": "ok"}`).

---

### 17. Frontend Requirements
- Built in Streamlit with Plotly visualizations:
  - **Trainer Console**: Document upload, volume selector, generated question list.
  - **SME Review Portal**: Interactive review queue displaying question details alongside source grounding context with edit and approval controls.
  - **Officer Quiz & Results Dashboard**: Assessment interface, score summaries, Plotly radar/bar charts, and recommended course cards.
  - **Admin View**: User, competency, and course management.
- *Styling & Component Details*: Not specified in the provided project documents beyond Streamlit + Plotly.

---

### 18. Integration Requirements
- **Mock iGOT REST Adapter**: Simulates course catalogue and enrollment contracts without requiring production iGOT credentials.
- **ChromaDB**: Local vector database for semantic chunk retrieval.
- **Mistral API**: LLM and embedding API endpoints for chunk vectorization and structured MCQ generation.

---

### 19. Prototype / MVP Scope
- **Included**: Role-at-registration authentication; document upload (PDF/PPT); RAG pipeline; MCQ generation; SME review queue; assessment engine; deterministic scoring; competency gap identification; sample public iGOT catalogue; mock iGOT REST adapter; explainable recommendations; reassessment loop.
- **Excluded / Out of Scope for MVP**: Production iGOT API access; official government single-sign-on (SSO) / Aadhaar / Parichay identity verification; full enterprise departmental hierarchy; certificate issuance; automated push notifications; complex multi-stage learning path orchestration.
- **Competency Framework Specification**: Not specified as a static official framework in the project documents; it is to be derived dynamically from the uploaded MoSPI reference materials.
- **Course Data Specification**: Real public iGOT courses used as sample data without fabricating course IDs or URLs.

---

### 20. Development Flow
14 sequential phases:
1. `Foundation`: FastAPI, PostgreSQL, SQLAlchemy, Alembic, environment configuration, health checks. *(Completed)*
2. `Database`: SQLAlchemy models, relationships, constraints, seed roles and initial data.
3. `Authentication`: Registration with role, password hashing, login, JWT issuance, RBAC.
4. `Document pipeline`: Upload, PDF/PPT text extraction, chunking, ChromaDB indexing, chunk traceability.
5. `MCQ generation`: Retriever + Mistral prompt + structured JSON output + Pydantic validation.
6. `SME validation`: Review queue, edit, approve/reject, and audit history.
7. `Assessment`: Assessment creation, question assignment, submission, deterministic scoring.
8. `Competency engine`: Grouping by competency, scoring, and skill gap identification.
9. `iGOT catalogue`: Collect real public iGOT course metadata, seed courses, map to competencies.
10. `iGOT adapter`: Expose course catalogue via mock REST contract.
11. `Recommendations`: Gap-to-course matching, priority scoring, explanation generation.
12. `Reassessment`: Second assessment and before/after proficiency comparison.
13. `Frontend integration`: Connect Streamlit UI to backend REST endpoints.
14. `Testing & Demo Preparation`: Integration tests, sample seed data, rehearsal for SIH evaluation.

---
---

## Part 2: Phase 1 — Backend Foundation Implementation Report

### 1. Files Created
1. `backend/requirements.txt`: Minimal Phase 1 dependencies.
2. `backend/.env.example`: Environment variables template.
3. `backend/.gitignore`: Python, environment, and Alembic ignore rules.
4. `backend/app/__init__.py`: Application package init.
5. `backend/app/main.py`: FastAPI app with CORS middleware, `GET /`, and `GET /health`.
6. `backend/app/core/__init__.py`: Core package init.
7. `backend/app/core/config.py`: Pydantic Settings configuration (`APP_NAME`, `DATABASE_URL`, `CORS_ORIGINS`, etc.).
8. `backend/app/db/__init__.py`: DB package exposing `Base`, `engine`, `SessionLocal`, and `get_db`.
9. `backend/app/db/base.py`: SQLAlchemy 2.x `DeclarativeBase` base class.
10. `backend/app/db/session.py`: Synchronous engine (`pool_pre_ping=True`), `SessionLocal`, and `get_db` dependency.
11. `backend/app/models/__init__.py`: Package placeholder for Phase 2 SQLAlchemy models.
12. `backend/app/schemas/__init__.py`: Package placeholder for Pydantic schemas.
13. `backend/app/routers/__init__.py`: Package placeholder for API routers.
14. `backend/app/services/__init__.py`: Package placeholder for business services.
15. `backend/app/ai/__init__.py`: Package placeholder for RAG/LLM modules (Phase 4–5).
16. `backend/app/integrations/__init__.py`: Package placeholder for Mock iGOT adapter (Phase 10).
17. `backend/alembic.ini`: Alembic migration configuration.
18. `backend/alembic/env.py`: Alembic environment connected to `Base.metadata` and application settings.
19. `backend/alembic/script.py.mako`: Migration script template.
20. `backend/alembic/versions/.gitkeep`: Migration versions folder placeholder.
21. `backend/tests/__init__.py`: Test suite package init.
22. `backend/tests/test_health.py`: Pytest test suite covering import, `GET /`, `GET /health`, settings loading, and DB engine/session instantiation.
23. `backend/README.md`: Comprehensive backend documentation.

### 2. Files Modified
- None (all backend files were newly created under `c:\SIH\backend`).

### 3. Dependencies Added
- `alembic` (1.20.0)
- `psycopg[binary]` (3.3.6)
- `pytest` (9.1.1)  
*(FastAPI, Uvicorn, SQLAlchemy 2.0.50, Pydantic v2, Pydantic-Settings, Python-Dotenv, and HTTPX were already present in the Python environment).*

### 4. Commands Executed
```powershell
# 1. Dependency installation
pip install alembic "psycopg[binary]" pytest

# 2. Application import check
python -c "import app.main; print('Import OK')"

# 3. Unit test execution
python -m pytest -v

# 4. Alembic configuration check
python -m alembic heads
python -c "from alembic.config import Config; from alembic.script import ScriptDirectory; cfg = Config('alembic.ini'); script = ScriptDirectory.from_config(cfg); print('Alembic config valid! Location:', script.dir)"

# 5. Live server execution and endpoint verification
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
python -c "import httpx; r1 = httpx.get('http://127.0.0.1:8000/'); print('GET / Status:', r1.status_code, r1.json()); r2 = httpx.get('http://127.0.0.1:8000/health'); print('GET /health Status:', r2.status_code, r2.json())"
```

### 5. Verification Results
1. **Application Import**:
   - `python -c "import app.main; print('Import OK')"` exited with code 0 and printed `Import OK`.
2. **FastAPI Live Server Response**:
   - `GET /` $\rightarrow$ Status `200`, JSON: `{"app": "StatKarmayogi", "version": "0.1.0", "docs": "/docs", "health": "/health"}`
   - `GET /health` $\rightarrow$ Status `200`, JSON: `{"status": "ok"}`
3. **Database Configuration**:
   - Pydantic Settings loaded `DATABASE_URL` as `postgresql+psycopg://...`.
   - Synchronous SQLAlchemy engine with `pool_pre_ping=True` verified.
   - `get_db` generator yielded a valid session and closed cleanly.
4. **Alembic Configuration**:
   - `alembic.ini` and `alembic/env.py` verified; target metadata configured to `Base.metadata`.
   - `python -m alembic heads` executed cleanly with exit code 0.
5. **Automated Pytest Results**:
   ```text
   tests/test_health.py::test_app_import PASSED                             [ 20%]
   tests/test_health.py::test_read_root PASSED                              [ 40%]
   tests/test_health.py::test_health_check PASSED                           [ 60%]
   tests/test_health.py::test_settings_loaded PASSED                        [ 80%]
   tests/test_health.py::test_database_configuration PASSED                 [100%]
   ============================== 5 passed in 0.77s ==============================
   ```

### 6. Errors Encountered
- None. All imports, migrations checks, tests, and live server endpoints passed cleanly.

### 7. Unresolved Issues
- None for Phase 1.

### 8. Confirmation of MVP Boundaries
- **No later-phase functionality was implemented**:
  - No database entity models created (`User`, `Role`, `Document`, `Question`, `Assessment`, `Course`, `Recommendation`).
  - No authentication, password hashing, or JWT tokens created.
  - No LangChain, ChromaDB, Mistral API, RAG, or MCQ generation pipelines created.
  - No SME review routes or assessment engines created.
  - No iGOT adapter logic created.

---
**Status**: Phase 1 is complete and verified. Ready for **Phase 2 — Database Schema** upon instruction.
