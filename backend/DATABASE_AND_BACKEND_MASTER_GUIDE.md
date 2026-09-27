# StatKarmayogi — Database & Backend Master Guide
## Authoritative As-Built Technical Report, Architecture Specification & Developer Reference

**Project:** StatKarmayogi — AI-Driven Competency Assessment & Adaptive iGOT Learning Pathway for MoSPI  
**SIH Problem Statement:** SIH26101  
**Target Ministry:** Ministry of Statistics and Programme Implementation (MoSPI), Government of India  
**Document Classification:** Final As-Built Technical Report & Master Backend Documentation  
**Implementation Date:** September 2026  
**System Status:** Core Database & Backend Prototype Fully Implemented, Unit Tested (174/174 Passed), and Live PostgreSQL Verified  

---

## Table of Contents
1. [Executive Overview](#part-1--executive-overview)
2. [System Architecture](#part-2--system-architecture)
3. [Complete Database Guide (16 Tables)](#part-3--complete-database-guide)
4. [Database Relationship Explanation](#part-4--database-relationship-explanation)
5. [Authentication and Role-Based Access Control (RBAC)](#part-5--authentication-and-rbac)
6. [Assessment Engine](#part-6--assessment-engine)
7. [Competency Model & Scoring Engine](#part-7--competency-model)
8. [Skill Gap Engine](#part-8--skill-gap-engine)
9. [Document-to-MCQ RAG Pipeline](#part-9--document--mcq-pipeline)
10. [iGOT Course Catalogue](#part-10--igot-course-catalogue)
11. [iGOT Adapter Architecture](#part-11--igot-adapter)
12. [Recommendation Engine & Mathematical Scoring](#part-12--recommendation-engine)
13. [Recommendation State Machine & Learning Progress](#part-13--recommendation-state-machine)
14. [Recommendation Reconciliation & Regeneration](#part-14--recommendation-regeneration)
15. [Reassessment Engine](#part-15--reassessment-engine)
16. [Before / After Comparison Mathematics](#part-16--before--after-comparison)
17. [Closed Learning Loop Semantics](#part-17--closed-learning-loop)
18. [Learning Activity Correlation & Educational Attribution](#part-18--learning-activity-correlation)
19. [Complete API Reference](#part-19--complete-api-reference)
20. [Complete End-to-End Data Trace](#part-20--complete-end-to-end-data-trace)
21. [Actual Data, Seed Records & Prototype Dataset](#part-21--actual-data--seed-data)
22. [Real vs. Prototype vs. Deterministic vs. AI Classification](#part-22--what-is-real-vs-mock-vs-deterministic-vs-ai)
23. [Transaction Boundaries & Data Integrity](#part-23--transaction-and-data-integrity)
24. [Error Handling & Edge Case Matrix](#part-24--error-handling)
25. [Testing & Verification Suite](#part-25--testing-and-verification)
26. [Database & Backend Invariants ("Do Not Break")](#part-26--database-and-backend-invariants)
27. [Developer Debugging & Troubleshooting Guide](#part-27--debugging-guide)
28. [Common Misunderstandings & Boundary Clarifications](#part-28--common-misunderstandings)
29. [Security & Sensitive Data Safeguards](#part-29--security--data-safety-notes)
30. [Current Prototype Limitations](#part-30--current-limitations)
31. [Future Extensions (Not Currently Implemented)](#part-31--future-extensions)
32. [Final System Summary](#part-32--final-system-summary)

---

## PART 1 — EXECUTIVE OVERVIEW

### 1.1 What StatKarmayogi Is
**StatKarmayogi** is an enterprise-grade AI-powered competency assessment and adaptive learning pathway platform developed for the **Ministry of Statistics and Programme Implementation (MoSPI)**, Government of India, under Smart India Hackathon problem statement **SIH26101**.

The platform provides a closed-loop human-capital development ecosystem for statistical officers across India (Indian Statistical Service - ISS, and Subordinate Statistical Service - SSS). It bridges the operational divide between official statistical manuals, diagnostic skill evaluations, and the Government of India’s **iGOT Karmayogi** capacity-building platform.

### 1.2 The Problem the Backend Solves
In public administration and national statistical operations, capacity building traditionally suffers from four structural bottlenecks:
1. **Disconnected Training:** Training courses on platforms like iGOT Karmayogi are often consumed without diagnostic pre-assessment, leading to generic learning rather than targeted upskilling.
2. **Untracked Competency Deficits:** Departmental leadership lacks granular, data-backed visibility into specific statistical competency gaps (e.g., Laspeyres index compilation, multi-stage stratified sampling, or Annual Survey of Industries methodology).
3. **Lack of Explainability:** Off-the-shelf course recommendations often use black-box algorithms that fail to explain *why* an officer needs a specific module.
4. **Open-Loop Interventions:** Once an officer completes a course, departments rarely administer a targeted reassessment to verify whether the identified skill gap was actually resolved.

StatKarmayogi's backend eliminates these deficiencies by executing a deterministic, auditable, and mathematically grounded **Closed Learning Loop**.

### 1.3 The Complete Backend Lifecycle
The backend orchestrates the lifecycle shown below:

```text
                      +-------------------+
                      |       USER        |
                      +-------------------+
                                |
                                v
                      +-------------------+
                      |  AUTHENTICATION   |  (Argon2id + JWT + RBAC)
                      +-------------------+
                                |
                                v
                      +-------------------+
                      |    ASSESSMENT     |  (Diagnostic Exam with Masked Keys)
                      +-------------------+
                                |
                                v
                      +-------------------+
                      |      ANSWERS      |  (Deterministic Evaluation)
                      +-------------------+
                                |
                                v
                      +-------------------+
                      |COMPETENCY RESULTS |  (Scores per MoSPI Competency)
                      +-------------------+
                                |
                                v
                      +-------------------+
                      |    SKILL GAPS     |  (HIGH, MEDIUM, LOW Gaps < 80%)
                      +-------------------+
                                |
                                v
                      +-------------------+
                      |  RECOMMENDATIONS  |  (Deterministic Match to iGOT Courses)
                      +-------------------+
                                |
                                v
                      +-------------------+
                      | LEARNING ACTIVITY |  (RECOMMENDED -> STARTED -> COMPLETED)
                      +-------------------+
                                |
                                v
                      +-------------------+
                      |   REASSESSMENT    |  (Targeted Post-Learning Evaluation)
                      +-------------------+
                                |
                                v
                      +-------------------+
                      |   BEFORE / AFTER  |  (Delta %, Resolution Status)
                      |    COMPARISON     |
                      +-------------------+
                                |
                                v
                      +-------------------+
                      |  CLOSED LEARNING  |  (LOOP_CLOSED, PARTIALLY_CLOSED,
                      |       LOOP        |   LOOP_OPEN Precedence)
                      +-------------------+
```

#### Lifecycle Stages Explained in Plain English:
1. **Authentication:** The officer authenticates using their institutional email and password. The system verifies their credentials using Argon2 hashing and issues an HMAC-SHA256 JWT access token encoding their identity and role.
2. **Assessment:** The officer initiates a diagnostic assessment. The backend draws approved multiple-choice questions from the database that are tagged to verified statistical competencies. Question answer keys and explanations are masked to preserve examination integrity.
3. **Answers & Scoring:** The officer submits their answers. The backend evaluates correctness in an atomic transaction, computing an overall score and individual scores for each competency tested.
4. **Competency Results:** Competency scores are mapped to four proficiency tiers: Beginner (<50%), Developing (50–64.99%), Proficient (65–79.99%), and Advanced (≥80%).
5. **Skill Gaps:** Any competency scoring below the 80% mastery threshold is identified as a skill gap and classified by severity: High (<50%), Medium (50–64.99%), or Low (65–79.99%).
6. **Course Recommendations:** The recommendation engine matches identified skill gaps against the iGOT course catalogue using deterministic weighting (`relevance * gap_multiplier * 100`). Each recommendation includes an explainable reason.
7. **Learning Activity:** The officer engages with the recommended training. The recommendation status advances through a strict state machine: `RECOMMENDED` &rarr; `STARTED` &rarr; `COMPLETED`.
8. **Reassessment:** After completing learning, a targeted reassessment is created for the officer, focusing specifically on the competencies where gaps originally existed.
9. **Before/After Comparison:** Upon submitting the reassessment, the backend computes the score delta for each competency, determines whether gaps are `RESOLVED`, `REDUCED`, `PERSISTENT`, or `INCREASED`, and correlates completed courses.
10. **Closed Learning Loop:** The macro state is evaluated: if all baseline gaps reach &ge;80%, the loop is `LOOP_CLOSED`; if some improved, it is `PARTIALLY_CLOSED`; if none improved, it remains `LOOP_OPEN`.

---

## PART 2 — SYSTEM ARCHITECTURE

### 2.1 Technology Stack & Core Components
The StatKarmayogi backend is built on a modern, asynchronous Python enterprise architecture:

- **Language:** Python 3.11+ / Python 3.14 compatible
- **Web Framework:** FastAPI (v0.115+) with Starlette
- **Data Validation & Settings:** Pydantic v2 & Pydantic Settings
- **ORM / Database Access:** SQLAlchemy 2.0 (Declarative Base, typed relationships)
- **Database Driver:** Psycopg 3 (`postgresql+psycopg://`)
- **Primary Database:** PostgreSQL 16+
- **Database Migrations:** Alembic
- **Vector Database (Content Pipeline):** ChromaDB (Local persistent client at `storage/chroma`)
- **Document Processing (RAG):** LangChain Community, PyPDF, python-pptx
- **AI / LLM Integration:** Mistral AI (`mistral-large-latest` for MCQs, `mistral-embed` for semantic embeddings)
- **Password Hashing:** Argon2id via `argon2-cffi`
- **Token Security:** PyJWT (HMAC-SHA256)
- **Testing Suite:** Pytest with AnyIO and FastAPI TestClient

### 2.2 Layered Architectural Diagram

```text
+-----------------------------------------------------------------------------------+
|                                  CLIENT LAYER                                     |
|           Streamlit Frontend (Port 8501) / Next.js / External Consumers           |
+-----------------------------------------------------------------------------------+
                                         |  HTTPS / REST JSON (JWT Bearer)
                                         v
+-----------------------------------------------------------------------------------+
|                                FASTAPI APPLICATION                                |
|                                   (app/main.py)                                   |
|   - CORS Middleware (Allow Origins: 8501, 3000, localhost)                        |
|   - OpenAPI 3.1 Swagger Docs (/docs, /redoc)                                      |
|   - Health & Root Monitoring (/health, /)                                         |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                                API ROUTERS LAYER                                  |
|                                 (app/routers/)                                    |
|   +-----------------------+-----------------------+---------------------------+   |
|   | auth.py               | documents.py          | questions.py              |   |
|   +-----------------------+-----------------------+---------------------------+   |
|   | assessments.py        | courses.py            | recommendations.py        |   |
|   +-----------------------+-----------------------+---------------------------+   |
|   | verification.py (RBAC validation test harness)                            |   |
+-----------------------------------------------------------------------------------+
         |                                |                               |
         | Dependencies                   | Model Schemas                 | Session Injection
         v                                v                               v
+------------------+             +------------------+            +------------------+
| app/core/        |             | app/schemas/     |            | app/db/session.py|
| - security.py    |             | Pydantic v2 DTOs |            | SessionLocal     |
| - dependencies.py|             | Request/Response |            | Engine Pool      |
+------------------+             +------------------+            +------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                            SERVICES & BUSINESS LOGIC                              |
|                                 (app/services/)                                   |
|   +------------------------------------+--------------------------------------+   |
|   | AssessmentService                  | ReassessmentService                  |   |
|   | - Creation & deterministic select  | - Title linkage parser & creation    |   |
|   | - Answer evaluation & scoring      | - Before/After comparison math       |   |
|   | - Competency results & skill gaps  | - Closed loop macro state precedence |   |
|   +------------------------------------+--------------------------------------+   |
|   | RecommendationService              | QuestionService & DocumentService    |   |
|   | - Deterministic candidate match    | - LangChain parser & text chunker    |   |
|   | - Active cap (6) & history keep    | - ChromaDB vector store wrapper      |   |
|   | - State machine status transitions | - Mistral RAG structured generation  |   |
|   +------------------------------------+--------------------------------------+   |
|   | AuthService                        | iGOT Adapter Boundary                |   |
|   | - Argon2id password verification   | - BaseIGOTAdapter (Abstract)         |   |
|   | - User registration & JWT issuing  | - MockIGOTAdapter (Local prototype)  |   |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                         SQLAlchemy 2.0 ORM MODELS                                 |
|                                  (app/models/)                                    |
|  User, Role, Document, DocumentChunk, Question, QuestionReview, Assessment,       |
|  AssessmentQuestion, Answer, Competency, CompetencyResult, SkillGap, Course,      |
|  CourseCompetency, Recommendation                                                 |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                            PERSISTENCE & STORAGE                                  |
|   +-----------------------------------------+---------------------------------+   |
|   | PostgreSQL Database (16 Tables)         | Local File & Vector Storage     |   |
|   | - Relational ACID storage               | - storage/documents (PDF, PPTX) |   |
|   | - FK Cascades & Constraints             | - storage/chroma (Embeddings)   |   |
+-----------------------------------------------------------------------------------+
```

---

## PART 3 — COMPLETE DATABASE GUIDE

The StatKarmayogi PostgreSQL database contains **exactly 16 tables** (15 application entities mapped via SQLAlchemy ORM plus the Alembic migration history table).

```text
+-----------------------------------------------------------------------------------+
|                       POSTGRESQL RELATIONAL SCHEMA MAP                            |
+-----------------------------------------------------------------------------------+

   +-------------+       1:N       +-------------+
   |    roles    | <-------------- |    users    |
   +-------------+                 +-------------+
                                      |   |   |
         +----------------------------+   |   +------------------------+
         | 1:N                            | 1:N                        | 1:N
         v                                v                            v
   +-------------+                 +-------------+              +-------------+
   |  documents  |                 | assessments |              |recommenda-  |
   +-------------+                 +-------------+              |   tions     |
         | 1:N                       |   |   |   |              +-------------+
         v                           |   |   |   | 1:N                 ^
   +-------------+                   |   |   |   +----------+          | 1:N
   |  document_  |                   |   |   | 1:N          |          |
   |   chunks    |                   |   |   v              v          |
   +-------------+                   |   | +-----------+  +----------+ |
         |                           |   | |competency_|  |  skill_  | |
         | 1:N                       |   | |  results  |  |   gaps   | |
         v                           |   | +-----------+  +----------+ |
   +-------------+                   |   |       |             |       |
   |  questions  |                   |   |       | N:1         | N:1   |
   +-------------+                   |   |       v             v       |
      |   |   ^                      |   |     +------------------+    |
  1:N |   |   +---------+            |   |     |   competencies   | <--+
      v   | 1:N         | 1:N        |   |     +------------------+
  +-----+ |             |            |   |               ^
  |quest| |             v            |   |               | N:1
  |_revs| |      +-------------+     |   |     +--------------------+
  +-----+ |      | assessment_ | <---+   |     |course_competencies |
          |      |  questions  |         |     +--------------------+
          |      +-------------+         |               | N:1
          |                              | 1:N           v
          |      +-------------+         |         +--------------+
          +----> |   answers   | <-------+         |   courses    |
                 +-------------+                   +--------------+
                                                          ^
                                                          | 1:N
                                      (referenced by recommendations)
```

### Detailed Table Specifications

#### 1. `roles`
- **Purpose:** Stores the authoritative system roles governing role-based access control.
- **Primary Key:** `id` (INTEGER, Autoincrement)
- **Columns:**
  - `id`: Unique role identifier.
  - `name`: Role name string (`VARCHAR(50)`, Unique, Non-nullable) representing `TRAINER`, `SME`, `OFFICER`, or `ADMIN`.
- **Foreign Keys:** None.
- **Relationships:** `users` (One-to-Many back-populates `role`).
- **Lifecycle:** Seeded idempotently at startup by `seed_roles()`. Static reference data.

#### 2. `users`
- **Purpose:** Represents authenticated user accounts, administrative personnel, trainers, subject matter experts, and statistical officers.
- **Primary Key:** `id` (INTEGER, Autoincrement)
- **Columns:**
  - `id`: Unique user identifier.
  - `name`: Full personal/officer name (`VARCHAR(255)`, Non-nullable).
  - `email`: Normalized lowercase unique email address (`VARCHAR(255)`, Unique, Indexed, Non-nullable).
  - `password_hash`: Secure Argon2id password hash (`VARCHAR(255)`, Non-nullable).
  - `role_id`: Role reference (`INTEGER`, Non-nullable, FK &rarr; `roles.id`).
  - `department`: Ministerial division or statistical office name (`VARCHAR(255)`, Nullable).
  - `designation`: Official rank/title, e.g., "Deputy Director", "Junior Statistical Officer" (`VARCHAR(255)`, Nullable).
  - `is_active`: Account status flag (`BOOLEAN`, Default: `True`, Non-nullable).
  - `created_at`: Account creation timestamp (`TIMESTAMP`, Non-nullable).
  - `updated_at`: Account modification timestamp (`TIMESTAMP`, Non-nullable).
- **Foreign Keys:** `role_id` &rarr; `roles.id`.
- **Relationships:**
  - `role`: Many-to-One back-populates `users`.
  - `documents`: One-to-Many (uploaded documents).
  - `questions_created`: One-to-Many (questions authored/generated).
  - `reviews`: One-to-Many (question audit decisions).
  - `assessments`: One-to-Many (assessments taken).
  - `recommendations`: One-to-Many (course recommendations received).
- **Lifecycle:** Created during user registration (`POST /api/v1/auth/register`) or seed routines. Consumed by authentication dependencies on every secured request.

#### 3. `documents`
- **Purpose:** Tracks official training documents, statistical manuals, survey frameworks, and guidelines uploaded by Trainers and Admins.
- **Primary Key:** `id` (INTEGER, Autoincrement)
- **Columns:**
  - `id`: Unique document record identifier.
  - `uploaded_by`: Uploader identifier (`INTEGER`, Non-nullable, FK &rarr; `users.id`).
  - `filename`: Sanitized original filename (`VARCHAR(255)`, Non-nullable).
  - `file_type`: Normalized file extension uppercase (`VARCHAR(50)`, e.g., 'PDF', 'PPTX').
  - `file_path`: Absolute or relative path on server filesystem (`VARCHAR(500)`, Non-nullable).
  - `status`: Ingestion status (`VARCHAR(10)`, Enum: `UPLOADED`, `PROCESSING`, `PROCESSED`, `FAILED`).
  - `processing_error`: Detailed error description if ingestion failed (`TEXT`, Nullable).
  - `generation_count`: Total MCQs successfully generated from this document (`INTEGER`, Default: 0).
  - `created_at`: Upload timestamp (`TIMESTAMP`, Non-nullable).
  - `updated_at`: Status transition timestamp (`TIMESTAMP`, Non-nullable).
- **Foreign Keys:** `uploaded_by` &rarr; `users.id`.
- **Relationships:** `uploader` (User), `chunks` (One-to-Many `document_chunks`), `questions` (One-to-Many `questions`).
- **Lifecycle:** Created by `POST /api/v1/documents`. Updated during chunking and MCQ generation.

#### 4. `document_chunks`
- **Purpose:** Stores granular text segments extracted from processed documents, preserving structural page/slide citations and providing relational linkage to vector embeddings in ChromaDB.
- **Primary Key:** `id` (INTEGER, Autoincrement)
- **Columns:**
  - `id`: Unique relational chunk identifier (referenced by LLM prompts and generated questions).
  - `document_id`: Parent document reference (`INTEGER`, Non-nullable, FK &rarr; `documents.id` ON DELETE CASCADE).
  - `chunk_index`: 0-indexed sequential position within the document (`INTEGER`, Non-nullable).
  - `page_number`: 1-indexed document page or presentation slide number (`INTEGER`, Nullable).
  - `content_hash`: SHA-256 hash of raw chunk text for deduplication verification (`VARCHAR(64)`, Nullable).
  - `chroma_id`: UUID string key corresponding to the vector record in ChromaDB (`VARCHAR(255)`, Nullable).
  - `created_at`: Ingestion timestamp (`TIMESTAMP`, Non-nullable).
- **Foreign Keys:** `document_id` &rarr; `documents.id`.
- **Relationships:** `document` (Many-to-One), `questions` (One-to-Many `questions.source_chunk_id`).
- **Lifecycle:** Created by `DocumentService.upload_and_process`. Consumed during similarity search and MCQ grounding.

#### 5. `competencies`
- **Purpose:** Defines the standardized MoSPI competency framework (e.g., Sampling Design, Index Numbers, ASI Methodology, National Accounts).
- **Primary Key:** `id` (INTEGER, Autoincrement)
- **Columns:**
  - `id`: Unique competency identifier.
  - `code`: Standardized ministerial code (`VARCHAR(100)`, Unique, Non-nullable).
  - `name`: Human-readable competency title (`VARCHAR(255)`, Non-nullable).
  - `description`: Detailed operational definition (`TEXT`, Nullable).
  - `category`: Functional domain classification, e.g., "Economic Statistics", "Survey Operations" (`VARCHAR(100)`, Nullable).
  - `is_active`: Operational availability flag (`BOOLEAN`, Default: `True`, Non-nullable).
  - `created_at`: Creation timestamp (`TIMESTAMP`, Non-nullable).
  - `updated_at`: Last modification timestamp (`TIMESTAMP`, Non-nullable).
- **Foreign Keys:** None.
- **Relationships:** `questions`, `competency_results`, `skill_gaps`, `course_competencies`, `recommendations`.
- **Lifecycle:** Seeded reference data representing MoSPI competency taxonomy.

#### 6. `questions`
- **Purpose:** Repository of diagnostic multiple-choice questions grounded in uploaded documents and mapped to competencies.
- **Primary Key:** `id` (INTEGER, Autoincrement)
- **Columns:**
  - `id`: Unique question identifier.
  - `document_id`: Source document reference (`INTEGER`, Nullable, FK &rarr; `documents.id`).
  - `competency_id`: Mapped competency reference (`INTEGER`, Nullable, FK &rarr; `competencies.id`).
  - `question_text`: Complete MCQ prompt text (`TEXT`, Non-nullable).
  - `option_a`: Choice text for option A (`TEXT`, Non-nullable).
  - `option_b`: Choice text for option B (`TEXT`, Non-nullable).
  - `option_c`: Choice text for option C (`TEXT`, Non-nullable).
  - `option_d`: Choice text for option D (`TEXT`, Non-nullable).
  - `correct_option`: Correct answer key (`VARCHAR(1)`, Values: 'A', 'B', 'C', 'D', Non-nullable).
  - `difficulty`: Calibrated difficulty (`VARCHAR(6)`, Enum: `EASY`, `MEDIUM`, `HARD`, Non-nullable).
  - `explanation`: Pedagogical rationale citing source facts (`TEXT`, Nullable).
  - `source_page`: Cited document page or slide number (`INTEGER`, Nullable).
  - `source_chunk_id`: Cited relational chunk identifier (`INTEGER`, Nullable, FK &rarr; `document_chunks.id`).
  - `generation_model`: LLM model identifier used for generation (`VARCHAR(100)`, Nullable).
  - `status`: SME review status (`VARCHAR(14)`, Enum: `PENDING_REVIEW`, `APPROVED`, `REJECTED`, Default: `PENDING_REVIEW`).
  - `created_by`: User ID of generator/author (`INTEGER`, Non-nullable, FK &rarr; `users.id`).
  - `created_at`: Generation timestamp (`TIMESTAMP`, Non-nullable).
  - `updated_at`: Review/update timestamp (`TIMESTAMP`, Non-nullable).
- **Foreign Keys:** `document_id` &rarr; `documents.id`, `competency_id` &rarr; `competencies.id`, `source_chunk_id` &rarr; `document_chunks.id`, `created_by` &rarr; `users.id`.
- **Relationships:** `document`, `competency`, `source_chunk`, `creator`, `reviews`, `assessment_questions`, `answers`.
- **Lifecycle:** Created by `POST /api/v1/questions/generate`. Updated to `APPROVED` or `REJECTED` by `POST /api/v1/questions/{id}/review`.

#### 7. `question_reviews`
- **Purpose:** Auditable governance log recording human-in-the-loop SME validation decisions for generated questions.
- **Primary Key:** `id` (INTEGER, Autoincrement)
- **Columns:**
  - `id`: Unique review record identifier.
  - `question_id`: Reviewed question reference (`INTEGER`, Non-nullable, FK &rarr; `questions.id` ON DELETE CASCADE).
  - `reviewer_id`: SME or Admin user ID (`INTEGER`, Non-nullable, FK &rarr; `users.id`).
  - `action`: Audit decision (`VARCHAR(7)`, Values: `APPROVE`, `REJECT`, Non-nullable).
  - `comment`: Justification or feedback notes (`TEXT`, Nullable).
  - `created_at`: Review timestamp (`TIMESTAMP`, Non-nullable).
- **Foreign Keys:** `question_id` &rarr; `questions.id`, `reviewer_id` &rarr; `users.id`.
- **Relationships:** `question`, `reviewer`.
- **Lifecycle:** Appended when an SME calls `POST /api/v1/questions/{id}/review`. Immutable audit trail.

#### 8. `assessments`
- **Purpose:** Core diagnostic examination instances administered to officers (both baseline diagnostic assessments and subsequent targeted reassessments).
- **Primary Key:** `id` (INTEGER, Autoincrement)
- **Columns:**
  - `id`: Unique assessment identifier.
  - `officer_id`: Candidate officer reference (`INTEGER`, Non-nullable, FK &rarr; `users.id`).
  - `title`: Assessment title (`VARCHAR(255)`, Non-nullable). For reassessments, encodes baseline linkage canonically: `Reassessment [Baseline #{id}]: {title}`.
  - `status`: Execution state (`VARCHAR(11)`, Enum: `IN_PROGRESS`, `COMPLETED`, Default: `IN_PROGRESS`).
  - `total_questions`: Number of assigned questions (`INTEGER`, Default: 0).
  - `total_correct`: Number of evaluated correct answers (`INTEGER`, Default: 0).
  - `score_percentage`: Overall percentage score (`NUMERIC(5, 2)`, Default: 0.00).
  - `started_at`: Assessment initialization timestamp (`TIMESTAMP`, Non-nullable).
  - `completed_at`: Final answer submission timestamp (`TIMESTAMP`, Nullable).
- **Foreign Keys:** `officer_id` &rarr; `users.id`.
- **Relationships:** `officer`, `assessment_questions`, `answers`, `competency_results`, `skill_gaps`, `recommendations`.
- **Lifecycle:** Created by `POST /api/v1/assessments` or `POST /api/v1/assessments/{id}/reassess`. Transitioned to `COMPLETED` by `POST /api/v1/assessments/{id}/submit`.

#### 9. `assessment_questions`
- **Purpose:** Join table linking specific approved questions to an assessment, enforcing question order and serving as the immutable exam manifest.
- **Primary Key:** `id` (INTEGER, Autoincrement)
- **Columns:**
  - `id`: Unique join record identifier.
  - `assessment_id`: Parent assessment reference (`INTEGER`, Non-nullable, FK &rarr; `assessments.id` ON DELETE CASCADE).
  - `question_id`: Assigned question reference (`INTEGER`, Non-nullable, FK &rarr; `questions.id`).
  - `question_order`: 1-indexed presentation order for the exam (`INTEGER`, Non-nullable).
- **Foreign Keys:** `assessment_id` &rarr; `assessments.id`, `question_id` &rarr; `questions.id`.
- **Relationships:** `assessment`, `question`.
- **Lifecycle:** Created during assessment creation. Immutable throughout the exam lifecycle.

#### 10. `answers`
- **Purpose:** Records an officer's selected options and individual evaluation results for assigned assessment questions.
- **Primary Key:** `id` (INTEGER, Autoincrement)
- **Columns:**
  - `id`: Unique answer record identifier.
  - `assessment_id`: Parent assessment reference (`INTEGER`, Non-nullable, FK &rarr; `assessments.id` ON DELETE CASCADE).
  - `question_id`: Assigned question reference (`INTEGER`, Non-nullable, FK &rarr; `questions.id`).
  - `selected_option`: Option chosen by candidate (`VARCHAR(1)`, Values: 'A', 'B', 'C', 'D', Non-nullable).
  - `is_correct`: Deterministic evaluation result against `Question.correct_option` (`BOOLEAN`, Non-nullable).
  - `answered_at`: Submission timestamp (`TIMESTAMP`, Non-nullable).
- **Foreign Keys:** `assessment_id` &rarr; `assessments.id`, `question_id` &rarr; `questions.id`.
- **Relationships:** `assessment`, `question`.
- **Lifecycle:** Created atomically when `POST /api/v1/assessments/{id}/submit` is called.

#### 11. `competency_results`
- **Purpose:** Stores aggregated performance metrics and proficiency levels computed for each competency evaluated in an assessment.
- **Primary Key:** `id` (INTEGER, Autoincrement)
- **Columns:**
  - `id`: Unique result record identifier.
  - `assessment_id`: Evaluated assessment reference (`INTEGER`, Non-nullable, FK &rarr; `assessments.id` ON DELETE CASCADE).
  - `competency_id`: Evaluated competency reference (`INTEGER`, Non-nullable, FK &rarr; `competencies.id`).
  - `questions_attempted`: Number of questions testing this competency (`INTEGER`, Default: 0).
  - `questions_correct`: Number of correct answers (`INTEGER`, Default: 0).
  - `score_percentage`: Competency percentage score (`NUMERIC(5, 2)`, Default: 0.00).
  - `proficiency_level`: Deterministic tier (`VARCHAR(10)`, Enum: `BEGINNER`, `DEVELOPING`, `PROFICIENT`, `ADVANCED`, Non-nullable).
  - `created_at`: Computation timestamp (`TIMESTAMP`, Non-nullable).
- **Foreign Keys:** `assessment_id` &rarr; `assessments.id`, `competency_id` &rarr; `competencies.id`.
- **Relationships:** `assessment`, `competency`.
- **Lifecycle:** Created atomically upon assessment submission. Consumed by results views and reassessment comparison.

#### 12. `skill_gaps`
- **Purpose:** Identifies and classifies competency deficits requiring capacity building (persisted for any competency scoring < 80.0%).
- **Primary Key:** `id` (INTEGER, Autoincrement)
- **Columns:**
  - `id`: Unique skill gap record identifier.
  - `assessment_id`: Assessed examination reference (`INTEGER`, Non-nullable, FK &rarr; `assessments.id` ON DELETE CASCADE).
  - `competency_id`: Deficient competency reference (`INTEGER`, Non-nullable, FK &rarr; `competencies.id`).
  - `score_percentage`: Exact percentage achieved in diagnostic assessment (`NUMERIC(5, 2)`, Non-nullable).
  - `gap_level`: Deficit severity (`VARCHAR(6)`, Enum: `HIGH`, `MEDIUM`, `LOW`, Non-nullable).
  - `created_at`: Generation timestamp (`TIMESTAMP`, Non-nullable).
- **Foreign Keys:** `assessment_id` &rarr; `assessments.id`, `competency_id` &rarr; `competencies.id`.
- **Relationships:** `assessment`, `competency`.
- **Lifecycle:** Generated atomically upon assessment submission. Serves as direct input to the recommendation engine and targeted reassessment generation.

#### 13. `courses`
- **Purpose:** Stores course metadata aligned with the iGOT Karmayogi catalogue.
- **Primary Key:** `id` (INTEGER, Autoincrement)
- **Columns:**
  - `id`: Unique internal course identifier.
  - `igot_course_id`: External or prototype iGOT identifier (`VARCHAR(100)`, Indexed, Nullable), e.g., 'IGOT-PROTO-ASI-01'.
  - `title`: Course module title (`VARCHAR(255)`, Non-nullable).
  - `description`: Overview of curriculum and learning objectives (`TEXT`, Nullable).
  - `provider`: Institutional training body, e.g., 'NSSTA', 'ESD MoSPI' (`VARCHAR(255)`, Nullable).
  - `language`: Medium of instruction (`VARCHAR(50)`, Default: 'English', Nullable).
  - `difficulty`: Target audience level (`VARCHAR(50)`, e.g., 'Beginner', 'Intermediate', 'Hard', Nullable).
  - `duration_minutes`: Estimated time to complete (`INTEGER`, Nullable).
  - `course_url`: Link to portal or placeholder (`VARCHAR(500)`, Nullable).
  - `is_public`: Visibility flag (`BOOLEAN`, Default: `True`, Non-nullable).
  - `is_active`: Availability flag for recommendations (`BOOLEAN`, Default: `True`, Non-nullable).
  - `source`: Platform origin (`VARCHAR(100)`, Default: 'iGOT Karmayogi', Nullable).
  - `created_at`: Creation timestamp (`TIMESTAMP`, Non-nullable).
  - `updated_at`: Modification timestamp (`TIMESTAMP`, Non-nullable).
- **Foreign Keys:** None.
- **Relationships:** `course_competencies`, `recommendations`.
- **Lifecycle:** Seeded via `seed_courses.py`. Queried by `/api/v1/courses` and recommendation matching.

#### 14. `course_competencies`
- **Purpose:** Many-to-Many associative bridge mapping courses to the specific competencies they address, qualified by domain relevance scores.
- **Primary Key:** `id` (INTEGER, Autoincrement)
- **Columns:**
  - `id`: Unique mapping record identifier.
  - `course_id`: Mapped course reference (`INTEGER`, Non-nullable, FK &rarr; `courses.id` ON DELETE CASCADE).
  - `competency_id`: Addressed competency reference (`INTEGER`, Non-nullable, FK &rarr; `competencies.id` ON DELETE CASCADE).
  - `relevance_score`: Domain relevance weight (`NUMERIC(3, 2)`, Range: 0.01 to 1.00, Default: 1.00, Non-nullable).
  - `created_at`: Mapping timestamp (`TIMESTAMP`, Non-nullable).
- **Foreign Keys:** `course_id` &rarr; `courses.id`, `competency_id` &rarr; `competencies.id`.
- **Relationships:** `course`, `competency`.
- **Lifecycle:** Populated during course seeding. Crucial relational bridge for deterministic recommendation scoring.

#### 15. `recommendations`
- **Purpose:** Stores personalized, explainable iGOT course recommendations generated for officers based on identified skill gaps.
- **Primary Key:** `id` (INTEGER, Autoincrement)
- **Columns:**
  - `id`: Unique recommendation record identifier.
  - `officer_id`: Candidate officer reference (`INTEGER`, Non-nullable, FK &rarr; `users.id`).
  - `assessment_id`: Generating assessment reference (`INTEGER`, Non-nullable, FK &rarr; `assessments.id`).
  - `competency_id`: Targeted deficient competency reference (`INTEGER`, Non-nullable, FK &rarr; `competencies.id`).
  - `course_id`: Recommended course reference (`INTEGER`, Non-nullable, FK &rarr; `courses.id`).
  - `priority`: Urgency tier (`INTEGER`, Values: 1 for HIGH, 2 for MEDIUM, 3 for LOW, Default: 1).
  - `match_score`: Deterministic composite score percentage (`NUMERIC(5, 2)`, Non-nullable).
  - `reason`: Pedagogical explanation of recommendation basis (`TEXT`, Non-nullable).
  - `status`: Lifecycle progress (`VARCHAR(11)`, Enum: `RECOMMENDED`, `STARTED`, `COMPLETED`, `DISMISSED`, Default: `RECOMMENDED`).
  - `created_at`: Generation timestamp (`TIMESTAMP`, Non-nullable).
- **Foreign Keys:** `officer_id` &rarr; `users.id`, `assessment_id` &rarr; `assessments.id`, `competency_id` &rarr; `competencies.id`, `course_id` &rarr; `courses.id`.
- **Relationships:** `officer`, `assessment`, `competency`, `course`.
- **Lifecycle:** Created automatically upon assessment submission or manually via `POST /api/v1/assessments/{id}/recommendations`. Status updated via `PATCH /api/v1/recommendations/{id}/status`.

#### 16. `alembic_version`
- **Purpose:** Core metadata table managed by Alembic to track the current database schema revision.
- **Primary Key:** `version_num` (`VARCHAR(32)`, Non-nullable).
- **Foreign Keys:** None.
- **Lifecycle:** Created and managed by Alembic CLI migration commands.

---

## PART 4 — DATABASE RELATIONSHIP EXPLANATION

The relational architecture is intentionally structured to preserve strict separation of concerns, examination security, and historical auditability:

### Why an Assessment Belongs to an Officer (`assessments.officer_id` &rarr; `users.id`)
Assessments are personal diagnostic instruments. An assessment belongs to an officer to establish unambiguous data ownership and enforce strict RBAC. Officers can only view and submit their own assessments; unauthorized cross-officer access is rejected with HTTP 403 Forbidden.

### Why `assessment_questions` Exists Separately from `questions` and `assessments`
When an assessment is created, a specific subset of approved questions is selected. The `assessment_questions` join table freezes this assignment:
1. It records the exact list of questions assigned to that specific assessment instance.
2. It dictates the fixed presentation order (`question_order`).
3. If questions are later edited or retired in the main question bank, the historical integrity of already-generated assessments remains completely unaffected.

### Why `answers` Are Separate from `assessment_questions`
`assessment_questions` represents the question *manifest* (what was asked). `answers` represents the candidate's *submission* (what option was selected and whether it was correct). Separating them enables:
- Delivery of masked questions while `IN_PROGRESS` without having to initialize null answer rows.
- Atomic validation that every assigned question has an answer upon submission.
- Independent querying of submission timestamps.

### Why `competency_results` Are Separate from `skill_gaps`
Every competency tested in an assessment produces a `competency_result`, even if the officer demonstrated full mastery (&ge;80%). In contrast, `skill_gaps` records *only* the actionable deficits (<80%). This distinction ensures:
- Full diagnostic transparency: officers and administrators can inspect competencies where the officer excelled (`ADVANCED`).
- Targeted downstream workflows: recommendation algorithms and targeted reassessments query `skill_gaps` directly without having to filter results repeatedly.

### Why `course_competencies` Is a Many-to-Many Bridge
A single comprehensive training course (e.g., "Annual Survey of Industries: Frame, Concepts & Sampling") often covers multiple competencies (e.g., Industrial Classification, Frame Sampling, and GVA Estimation). Conversely, a competency can be addressed by multiple courses with varying depths. The bridge table models this reality and includes a `relevance_score` (0.01–1.00) quantifying how strongly the course addresses each competency.

### Why `recommendations` References Courses and Gaps Directly
A recommendation is the intersection of an identified `SkillGap` and an available `Course`. By persisting `competency_id`, `course_id`, `assessment_id`, and `officer_id`, the system maintains a complete audit trail:
- Why the course was recommended (linked to the exact diagnostic score).
- Which competency deficit it was intended to resolve.
- What status the officer achieved in completing the module.

### Why Recommendation History Is Preserved
When recommendations are regenerated, the system **never deletes or modifies** records in `STARTED`, `COMPLETED`, or `DISMISSED` status. Learning activity represents historical effort. Wiping out a `COMPLETED` course record upon taking a new assessment would destroy the officer's capacity-building record and prevent longitudinal correlation during reassessment.

### Why Multiple Assessment Instances Are Allowed
StatKarmayogi does not overwrite prior assessments. An officer may take:
- Baseline Assessment #1 (Diagnostic).
- Reassessment #1 (Attempt 1 after completing Course A).
- Reassessment #2 (Attempt 2 after completing Course B).
Each is an immutable assessment record with its own timestamp, score, and questions.

---

## PART 5 — AUTHENTICATION AND RBAC

### 5.1 Authentication Mechanism
StatKarmayogi implements stateless token-based authentication using **Argon2id** password hashing and **HMAC-SHA256 JWT** tokens:

1. **Password Hashing:** Passwords are hashed using the Argon2id algorithm via `argon2-cffi` (`PasswordHasher`), providing state-of-the-art resistance against GPU-based brute-force and side-channel attacks.
2. **Login Endpoints:**
   - `POST /api/v1/auth/login`: Standard JSON login accepting `{"email": "...", "password": "..."}`.
   - `POST /api/v1/auth/token`: OAuth2-compatible form-urlencoded login (`username`, `password`) facilitating interactive Swagger UI authentication.
3. **Constant-Time Verification:** To prevent timing attacks, password verification executes against a constant-time check; invalid emails and incorrect passwords both return a generic HTTP 401 Unauthorized (`"Invalid email or password."`).
4. **Token Generation:** Upon successful authentication, the backend issues a signed JWT containing:
   - `sub`: User ID (as a string).
   - `role`: Canonical role name string (`OFFICER`, `ADMIN`, `TRAINER`, `SME`).
   - `exp`: Expiration timestamp (default: 60 minutes from issue).
   - `iat`: Issue timestamp.
5. **Session Resolution:** On protected routes, the `get_current_user` dependency decodes the Bearer token, verifies signature and expiration, retrieves the active user record from PostgreSQL, and verifies that `is_active == True`.

### 5.2 Role-Based Access Control (RBAC) Matrix
StatKarmayogi defines four distinct system roles with strictly enforced boundaries:

| Functional Operation | OFFICER | ADMIN | TRAINER | SME |
| :--- | :---: | :---: | :---: | :---: |
| **Self-Registration** (`/auth/register`) | Yes | No (Admin registration blocked) | Yes | Yes |
| **Upload Document** (`POST /documents`) | 403 Forbidden | Yes | Yes | 403 Forbidden |
| **Delete Document** (`DELETE /documents/{id}`) | 403 Forbidden | Yes | Yes (Own uploads only) | 403 Forbidden |
| **Generate MCQs** (`POST /questions/generate`) | 403 Forbidden | Yes | Yes | 403 Forbidden |
| **Review / Audit MCQ** (`POST /questions/{id}/review`) | 403 Forbidden | Yes | 403 Forbidden | Yes |
| **Create Assessment** (`POST /assessments`) | Yes (Self only) | Yes (Any officer) | 403 Forbidden | 403 Forbidden |
| **Submit Assessment** (`POST /assessments/{id}/submit`) | Yes (Own only) | Yes (Own only) | 403 Forbidden | 403 Forbidden |
| **View Assessment Results** (`GET /assessments/{id}/result`)| Yes (Own only) | Yes | Yes | 403 Forbidden |
| **Create Reassessment** (`POST /assessments/{id}/reassess`) | Yes (Own baseline) | Yes | 403 Forbidden | 403 Forbidden |
| **View Reassessment Comparison** (`GET /.../comparison`) | Yes (Own only) | Yes | Yes | 403 Forbidden |
| **Generate Recommendations** (`POST /.../recommendations`)| Yes (Own only) | Yes | 403 Forbidden | 403 Forbidden |
| **View Recommendations** (`GET /recommendations`) | Yes (Own only) | Yes | Yes | 403 Forbidden |
| **Update Recommendation Status** (`PATCH /.../status`) | Yes (Own only) | Yes | 403 Forbidden | 403 Forbidden |
| **Browse Courses Catalogue** (`GET /courses`) | Yes | Yes | Yes | Yes |

*Note: SME accounts are dedicated exclusively to content quality validation and question bank review; they are strictly barred from taking assessments, viewing officer results, or inspecting recommendation pathways.*

---

## PART 6 — ASSESSMENT ENGINE

### 6.1 Complete Assessment Lifecycle
The assessment engine provides secure, deterministic diagnostic evaluations:

```text
1. POST /api/v1/assessments
   (question_count, optional competency_id/document_id)
      │
      ├─► Validate caller role (OFFICER or ADMIN)
      ├─► Query Question table for status == APPROVED and competency_id IS NOT NULL
      ├─► Apply deterministic ordering: ORDER BY questions.id ASC
      ├─► Verify available count >= requested count
      ├─► Insert into assessments (status = IN_PROGRESS)
      └─► Insert into assessment_questions (manifest with question_order)

2. GET /api/v1/assessments/{id}
      │
      └─► Return questions with safe exam masking:
          - option_a, option_b, option_c, option_d visible
          - correct_option, explanation, source_page, source_chunk STRICTLY HIDDEN

3. POST /api/v1/assessments/{id}/submit
   (answers: [{question_id, selected_option}, ...])
      │
      ├─► Verify caller is owner of assessment (or ADMIN)
      ├─► Verify assessment status == IN_PROGRESS
      ├─► Validate answer completeness:
      │   - No duplicate question submissions
      │   - No unassigned question IDs
      │   - Exact 1-to-1 match with assigned manifest
      │
      ├─► [ATOMIC TRANSACTION BEGINS]
      │   ├─► Evaluate correctness against Question.correct_option
      │   ├─► Insert/upsert records into answers
      │   ├─► Group results by competency_id
      │   ├─► Compute overall score: (total_correct / total_questions) * 100
      │   ├─► Update assessment (status = COMPLETED, score_percentage, completed_at)
      │   ├─► Compute competency scores and assign ProficiencyLevel
      │   ├─► Insert records into competency_results
      │   ├─► Identify deficiencies (< 80%) and insert into skill_gaps (HIGH/MED/LOW)
      │   └─► [COMMIT TRANSACTION]
      │
      └─► [SAFE RECOMMENDATION HOOK]
          ├─► Trigger RecommendationService.generate_recommendations()
          └─► If recommendation generation encounters an issue, catch and log:
              assessment remains COMPLETED and fully valid.
```

### 6.2 Concrete Worked Example
1. Officer Ramesh takes a 10-question baseline assessment covering three competencies:
   - **Competency A (ASI Survey Methodology):** 4 questions assigned.
   - **Competency B (Index of Industrial Production):** 4 questions assigned.
   - **Competency C (Sample Survey Design):** 2 questions assigned.
2. Officer submits answers:
   - Competency A: 1 correct out of 4 &rarr; **25.00%** &rarr; Proficiency: `BEGINNER`
   - Competency B: 3 correct out of 4 &rarr; **75.00%** &rarr; Proficiency: `PROFICIENT`
   - Competency C: 2 correct out of 2 &rarr; **100.00%** &rarr; Proficiency: `ADVANCED`
3. Overall Assessment Score:
   $$\text{Score} = \frac{1 + 3 + 2}{10} \times 100 = 60.00\%$$
4. Skill Gap Generation:
   - Competency A (25.00% < 50%) &rarr; Identified as **`HIGH`** severity skill gap.
   - Competency B (75.00% < 80%) &rarr; Identified as **`LOW`** severity skill gap.
   - Competency C (100.00% &ge; 80%) &rarr; Mastery achieved; **NO skill gap generated**.
5. Recommendation Engine Hook:
   - Automatically triggered for Assessment ID.
   - Receives SkillGap records for Competencies A and B.

---

## PART 7 — COMPETENCY MODEL

### 7.1 What a Competency Is
In StatKarmayogi, a **Competency** is a standardized, operational statistical capability required by MoSPI personnel to execute official statistical duties. Competencies are stored in the `competencies` table with unique ministerial codes (e.g., `ASI_METH_73F0`, `IIP_IND_94799B`, `COMP_NAD_3746b0`).

### 7.2 Proficiency Tiers and Thresholds
Proficiency is calculated deterministically from the percentage of correct answers achieved for each competency tested:

$$\text{Score Percentage} = \text{round}\left(\frac{\text{Questions Correct}}{\text{Questions Attempted}} \times 100, 2\right)$$

The score is mapped to four standard proficiency tiers configured in `app/core/config.py`:

| Proficiency Level | Score Range | Description |
| :--- | :---: | :--- |
| **`ADVANCED`** | **&ge; 80.0%** | Full operational mastery. Candidate demonstrates authoritative conceptual understanding. No skill gap is created. |
| **`PROFICIENT`** | **65.0% – 79.99%** | Solid operational competence. Minor refinements or refresher training recommended. |
| **`DEVELOPING`** | **50.0% – 64.99%** | Basic familiarity. Significant conceptual deficiencies exist requiring structured training. |
| **`BEGINNER`** | **< 50.0%** | Insufficient operational capability. Critical foundational training required. |

### 7.3 Significance of the 80% Mastery Threshold
The **80.0% threshold (`ADVANCED_THRESHOLD`)** is the central pivot of the StatKarmayogi competency framework:
- It represents the boundary of independent operational capability.
- Any score **below 80.0%** triggers an automated skill gap and course recommendation.
- During reassessment, a skill gap is marked as **`RESOLVED`** if and only if the officer reaches or exceeds **80.0%**.

---

## PART 8 — SKILL GAP ENGINE

### 8.1 Gap Severity Classification
Whenever an officer scores below the 80% mastery threshold in any assessed competency, the backend instantiates a `SkillGap` record. The gap severity is assigned deterministically:

$$\text{Gap Level} = \begin{cases} 
\text{HIGH} & \text{if } \text{score} < 50.0\% \\ 
\text{MEDIUM} & \text{if } 50.0\% \le \text{score} < 65.0\% \\ 
\text{LOW} & \text{if } 65.0\% \le \text{score} < 80.0\% \\ 
\text{None} & \text{if } \text{score} \ge 80.0\% \text{ (Mastery)} 
\end{cases}$$

### 8.2 Input, Processing, and Persistence
- **Inputs:** `assessment_id`, `competency_id`, `score_percentage`.
- **Processing:** Executed inside `AssessmentService.submit_assessment` within the primary database transaction.
- **Idempotency Guard:** Any pre-existing `skill_gaps` for that `assessment_id` are deleted before re-inserting to prevent duplicate records.
- **Persistence:** Saved directly to the `skill_gaps` table with `assessment_id`, `competency_id`, `score_percentage`, and `gap_level`.

### 8.3 Worked Calculation Example
Consider an assessment testing four distinct MoSPI competencies:

| Competency | Attempted | Correct | Score % | Proficiency Level | Gap Level Generated |
| :--- | :---: | :---: | :---: | :---: | :---: |
| National Accounts Statistics | 5 | 1 | 20.00% | `BEGINNER` | **`HIGH`** |
| Field Sampling Design | 4 | 2 | 50.00% | `DEVELOPING` | **`MEDIUM`** |
| IIP Laspeyres Index | 4 | 3 | 75.00% | `PROFICIENT` | **`LOW`** |
| Official Statistics Ethics | 3 | 3 | 100.00% | `ADVANCED` | *None (Mastery)* |

---

## PART 9 — DOCUMENT &rarr; MCQ PIPELINE

StatKarmayogi features an integrated Retrieval-Augmented Generation (RAG) content pipeline that converts official MoSPI documentation into grounded, SME-auditable diagnostic questions.

```text
 +-----------------------------------------------------------------------------------+
 |                              DOCUMENT INGESTION                                   |
 +-----------------------------------------------------------------------------------+
  Uploaded File (.pdf, .pptx)
       │
       ▼
  File Validation & Storage (MAX 20MB, storage/documents/)
       │
       ▼
  LangChain Parser (PyPDFLoader / python-pptx)
       │
       ▼
  Recursive Splitter (Chunk size: 1000 chars, Overlap: 150 chars)
       │
       ▼
  Mistral Embeddings (mistral-embed API)
       │
       ├─────────────────────────────────┐
       ▼                                 ▼
  ChromaDB Vector Store             PostgreSQL Database
  (Vector, Metadata, Chroma UUID)   (document_chunks: Relational Chunk ID,
                                     Page Number, Content Hash, Chroma UUID)

 +-----------------------------------------------------------------------------------+
 |                             RAG MCQ GENERATION                                    |
 +-----------------------------------------------------------------------------------+
  Trainer/Admin calls POST /api/v1/questions/generate (Document ID, Competency ID)
       │
       ▼
  Query Vector Generated & ChromaDB Top-K Similarity Search Executed
       │
       ▼
  Relational Cross-Reference: Chroma UUID &rarr; PostgreSQL document_chunks
       │
       ▼
  Grounding Context Assembled with explicit integer headers: [CHUNK ID: X, PAGE: Y]
       │
       ▼
  Mistral Large LLM (mistral-large-latest, temp=0.2) with Structured Output
       │
       ▼
  Quality Validation & Structural Checks:
  - 4 distinct options (no "All/None of the above")
  - Exactly one correct key ('A', 'B', 'C', or 'D')
  - Explicit source chunk attribution verified against retrieved set
  - Batch deduplication
       │
       ▼
  Single Transaction Commit:
  - Questions persisted with status PENDING_REVIEW
  - document.generation_count incremented

 +-----------------------------------------------------------------------------------+
 |                             HUMAN-IN-THE-LOOP AUDIT                               |
 +-----------------------------------------------------------------------------------+
  SME calls POST /api/v1/questions/{id}/review (Action: APPROVE or REJECT)
       │
       ▼
  Atomic Update:
  - question.status transitioned to APPROVED or REJECTED
  - Auditable QuestionReview record appended with reviewer ID and comment
       │
       ▼
  Only APPROVED questions with competency_id IS NOT NULL are eligible for exams.
```

### Deterministic vs. AI-Generated Boundaries
- **AI-Generated:** The phrasing of the question text, option distractors, and pedagogical explanation generated by `ChatMistralAI`.
- **Deterministic:** Document parsing, text chunking boundaries, SHA-256 content hashing, ChromaDB similarity retrieval, chunk ID attribution validation, option uniqueness checking, status transition logic, and SME review audit recording.

---

## PART 10 — iGOT COURSE CATALOGUE

### 10.1 Relational Architecture
Courses and their competency mappings are stored across two tables:
1. `courses`: Holds module metadata (provider, duration, difficulty, URL).
2. `course_competencies`: Associative bridge recording which competencies each course covers, along with a `relevance_score` (`NUMERIC(3, 2)`).

### 10.2 Prototype / Mock vs. Live iGOT Disclaimer
> [!IMPORTANT]
> The course records in the StatKarmayogi database are **curated prototype reference modules** designed to model the curriculum structure of MoSPI training bodies (such as NSSTA and the Economic Statistics Division) on the iGOT Karmayogi platform. They are **not live external iGOT API records**, and no live network connection to DoPT/iGOT production servers is asserted or required for the prototype.

### 10.3 The Six Curated Prototype Courses

| PK ID | iGOT Course ID | Title | Provider | Mapped Competencies | Relevance | Mapping Status |
| :---: | :--- | :--- | :--- | :--- | :---: | :---: |
| **93** | `IGOT-PROTO-ASI-01` | Annual Survey of Industries (ASI): Frame, Concepts & Sampling | MoSPI Training Division / NSSTA | `ASI_METH_73F0` (ASI Survey Methodology & Classification) | 0.95 | **Mapped** |
| **94** | `IGOT-PROTO-IIP-01` | Compilation of Index of Industrial Production (IIP) & Laspeyres Weighting | Economic Statistics Division (ESD), MoSPI | `IIP_IND_94799B` (Index of Industrial Production) | 0.90 | **Mapped** |
| **95** | `IGOT-PROTO-NAS-01` | National Accounts Statistics: Gross Value Added (GVA) & Fixed Capital | National Accounts Division (NAD), MoSPI | `COMP_NAD_3746b0` (National Accounts & GVA) | 0.95 | **Mapped** |
| **96** | `IGOT-PROTO-SSD-01` | Sample Survey Design & Multi-Stage Sampling in Official Statistics | Survey Design & Research Division (SDRD), MoSPI | `COMP_D981F6` (Sample Survey Design) | 0.90 | **Mapped** |
| **97** | `IGOT-PROTO-FPOS-01` | Fundamental Principles of Official Statistics & Data Ethics | NSSTA | *None* | *None* | **Intentionally Unmapped** |
| **98** | `IGOT-PROTO-DAP-01` | Data Analytics & Statistical Analysis for Field Officers | Computer Centre, MoSPI | *None* | *None* | **Intentionally Unmapped** |

### 10.4 Why FPOS and DAP Are Intentionally Unmapped
Courses 97 (`IGOT-PROTO-FPOS-01`) and 98 (`IGOT-PROTO-DAP-01`) have **zero mapping rows** in `course_competencies`.  
**Architectural Rationale:** In the verified MoSPI seed catalogue, no official competency corresponding to "Ethics in Official Statistics" or "General Field Analytics" was formally established. In adherence to the project’s strict integrity directives:
- **No artificial or fake competency mappings were fabricated.**
- **No arbitrary fallback competencies were assigned.**
- Courses without verified competency matches in the database remain unmapped until MoSPI SMEs formally define and approve those competency standards. Consequently, these two courses will never be inappropriately recommended for unrelated skill gaps.

---

## PART 11 — iGOT ADAPTER

### 11.1 Adapter Architecture & Interface Boundary
The iGOT integration boundary is isolated in `app/integrations/igot_adapter.py`. It decouples core business logic from external catalogue providers using an abstract base class:

```python
class BaseIGOTAdapter(ABC):
    @abstractmethod
    def get_courses(self, query: Optional[str] = None, competency_code: Optional[str] = None, skip: int = 0, limit: int = 20) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_course_by_id(self, igot_course_id: str) -> Optional[Dict[str, Any]]:
        pass
```

### 11.2 What the Adapter Currently Does
- Provides a clean integration boundary (`MockIGOTAdapter`) that serves local reference course metadata for discovery without making external network calls.
- Encapsulates course discovery and keyword filtering.

### 11.3 What the Adapter Does NOT Do
- It does **not** make live HTTP requests to DoPT or iGOT production servers.
- It does **not** perform live user enrollment or synchronize external learning progress.
- It is **not** part of the internal recommendation scoring formula. Course recommendations are computed directly in PostgreSQL via `CourseCompetency` join queries in `RecommendationService`.

---

## PART 12 — RECOMMENDATION ENGINE

### 12.1 Matching Workflow
When recommendations are generated for a completed assessment, the engine executes a deterministic multi-stage matching pipeline:

```text
 1. Query SkillGaps for Assessment
    (Filter: assessment_id == id)
         │
         ▼
 2. Join CourseCompetency and Course
    (Filter: competency_id == gap.competency_id AND course.is_active == True)
         │
         ▼
 3. Compute Deterministic Match Score & Priority
    - Priority: HIGH gap = 1, MEDIUM gap = 2, LOW gap = 3
    - Multiplier: HIGH = 1.00, MEDIUM = 0.85, LOW = 0.70
    - Match Score = round(relevance_score * multiplier * 100, 2)
         │
         ▼
 4. Intra-Gap Sort & Per-Gap Limit (MAX_RECOMMENDATIONS_PER_GAP = 2)
    - Sort: (priority ASC, -match_score DESC, -relevance_score DESC, course_id ASC)
    - Slice top 2 candidates per gap
         │
         ▼
 5. Inter-Gap Deduplication & Global Active Cap (MAX_TOTAL_ACTIVE_RECOMMENDATIONS = 6)
    - Deduplicate courses appearing in multiple gaps
    - Slice top 6 global candidates
         │
         ▼
 6. History-Preserving Reconciliation
    - Preserve STARTED and COMPLETED rows untouched
    - Respect DISMISSED rows
    - Refresh existing RECOMMENDED rows
    - Remove only unstarted RECOMMENDED rows that fell out of top 6
```

### 12.2 Mathematical Scoring Formula & Multipliers
The deterministic match score is defined as:

$$\text{Match Score} = \text{round}(\text{Relevance Score} \times \text{Gap Multiplier} \times 100, 2)$$

Where:
- **`Relevance Score`** is the decimal weight from `CourseCompetency.relevance_score` ($0.00 < r \le 1.00$).
- **`Gap Multiplier`** is determined by `SkillGap.gap_level`:
  - **`HIGH`** severity deficit: $\text{Multiplier} = 1.00$, $\text{Priority} = 1$
  - **`MEDIUM`** severity deficit: $\text{Multiplier} = 0.85$, $\text{Priority} = 2$
  - **`LOW`** severity deficit: $\text{Multiplier} = 0.70$, $\text{Priority} = 3$

#### Deterministic Tie-Breaking Key
Whenever multiple course candidates compete for recommendation slots, ties are broken deterministically using the tuple:
$$\text{Sort Key} = (\text{priority}, -\text{match\_score}, -\text{relevance\_score}, \text{course\_id})$$

### 12.3 Explainable Pedagogical Reason Generation
StatKarmayogi generates human-readable justifications explaining *why* the course was recommended:
```text
"Recommended because your assessment score in {competency_name} was {score_percentage}%, 
identified as a {gap_level} priority skill gap. This course has a {relevance_percentage}% domain 
relevance to this competency, resulting in a match score of {match_score}%."
```

### 12.4 Recommendation Limits & Historical Row Preservation
- **`MAX_RECOMMENDATIONS_PER_GAP`:** Configured to **2**. Prevents a single competency gap from flooding the officer's pathway.
- **`MAX_TOTAL_ACTIVE_RECOMMENDATIONS`:** Configured to **6**. Limits the total number of uncompleted active modules presented to the officer.
- **Why More Than 6 Rows Can Exist:** The limit applies **only to active recommendations**. As an officer completes courses (`COMPLETED`) or dismisses modules (`DISMISSED`), those historical records remain in the `recommendations` table forever. A long-serving officer may accumulate dozens of historical recommendation rows while having at most 6 active modules at any one time.

---

## PART 13 — RECOMMENDATION STATE MACHINE

### 13.1 State Machine Specification
Each recommendation follows a strict, non-reversible state machine:

```text
               +-------------------+
               |    RECOMMENDED    |  (Initial state created by engine)
               +-------------------+
                 /               \
   Officer starts course          Officer dismisses course
               /                   \
              v                     v
     +-----------------+   +-----------------+
     |     STARTED     |   |    DISMISSED    |  (Terminal state)
     +-----------------+   +-----------------+
              |
   Officer completes course
              |
              v
     +-----------------+
     |    COMPLETED    |  (Terminal state / eligible for reassessment context)
     +-----------------+
```

### 13.2 Allowed and Rejected Transitions

| Current Status | Target Status | Allowed? | API Response / Action |
| :--- | :--- | :---: | :--- |
| **`RECOMMENDED`** | `STARTED` | **Yes** | Status updated to `STARTED`. |
| **`RECOMMENDED`** | `DISMISSED` | **Yes** | Status updated to `DISMISSED`. |
| **`RECOMMENDED`** | `COMPLETED` | **No** | HTTP 400 Bad Request (`Invalid status transition`). |
| **`STARTED`** | `COMPLETED` | **Yes** | Status updated to `COMPLETED`. |
| **`STARTED`** | `DISMISSED` | **No** | HTTP 400 Bad Request (Cannot dismiss an in-progress course). |
| **`STARTED`** | `RECOMMENDED` | **No** | HTTP 400 Bad Request (Cannot revert to recommended). |
| **`COMPLETED`** | *Any* | **No** | HTTP 400 Bad Request (Terminal state; immutable). |
| **`DISMISSED`** | *Any* | **No** | HTTP 400 Bad Request (Terminal state; immutable). |

---

## PART 14 — RECOMMENDATION REGENERATION

### 14.1 Idempotency & History Protection
Officers or administrators can trigger recommendation regeneration at any time via `POST /api/v1/assessments/{id}/recommendations`. The reconciliation logic guarantees:
1. **Preservation of Engaged Modules:** Any recommendation record currently in `STARTED` or `COMPLETED` status is **never overwritten, mutated, or deleted**.
2. **Respect for Dismissals:** Any course previously marked `DISMISSED` by the officer is permanently excluded from re-recommendation for that assessment.
3. **Field Refreshing:** If a course is still in `RECOMMENDED` status, its `match_score`, `priority`, and `reason` are updated to reflect the latest scoring rules.
4. **Clean Pruning:** Only unstarted `RECOMMENDED` records that no longer qualify for the top active selection are pruned from the database.

---

## PART 15 — REASSESSMENT ENGINE

The Reassessment Engine completes the closed learning loop by providing targeted post-learning evaluations linked to an officer's original baseline diagnostic assessment.

```text
       BASELINE ASSESSMENT (e.g. Assessment #645)
       - Score: 0.00% (High Gap in Competency 278)
       - Status: COMPLETED
                          │
                          ▼
       RECOMMENDATION & LEARNING
       - Course #93 recommended
       - Status transitioned: RECOMMENDED &rarr; STARTED &rarr; COMPLETED
                          │
                          ▼
       POST /api/v1/assessments/645/reassess
                          │
                          ├─► Enforce baseline is COMPLETED (400 if in progress)
                          ├─► Enforce baseline is not already a reassessment (400)
                          ├─► Extract targeted competencies from baseline skill gaps
                          ├─► Draw approved questions for targeted competencies
                          ├─► Format canonical title: "Reassessment [Baseline #645]: ..."
                          └─► Create Reassessment #646 (status = IN_PROGRESS)
                                  │
                                  ▼
       OFFICER TAKES & SUBMITS REASSESSMENT
       - POST /api/v1/assessments/646/submit
       - Evaluated Score: 100.00%
       - Baseline #645 remains 100% IMMUTABLE
                                  │
                                  ▼
       GET /api/v1/assessments/646/comparison
       - Baseline Score: 0.00% | Reassessment Score: 100.00%
       - Delta: +100.00% (IMPROVED)
       - Competency Gap Resolution: RESOLVED
       - Macro Closed Loop Status: LOOP_CLOSED
       - Associated Learning: Course #93 (COMPLETED) with educational attribution
```

### 15.1 Zero Schema Changes via Canonical Title Linkage
To preserve strict database schema stability, baseline linkages are encoded directly into the reassessment title:
```text
Reassessment [Baseline #{baseline_id}]: {title}
```
- **Parsing Utility:** `parse_baseline_id_from_title(title)` uses regular expression `^Reassessment \[Baseline #(\d+)\]: (.+)$` to extract the baseline ID.
- **Linkage Integrity:** If a caller attempts to pass an explicit `?baseline_id=X` query parameter that conflicts with the title-encoded baseline ID, the API rejects the request with HTTP 400 Bad Request.

### 15.2 Baseline Immutability Guarantee
When a reassessment is created, submitted, or evaluated:
- **Zero baseline rows are modified.**
- The baseline's `status`, `score_percentage`, `completed_at`, `competency_results`, and `skill_gaps` remain completely unchanged.
- Reassessments are fully independent `Assessment` rows.

---

## PART 16 — BEFORE / AFTER COMPARISON

### 16.1 Mathematics & Delta Calculation
For every competency evaluated in the reassessment, the backend calculates:

$$\Delta = \text{round}(\text{Reassessment Score} - \text{Baseline Score}, 2)$$

- **`IMPROVED`:** $\Delta > 0.00$
- **`DECLINED`:** $\Delta < 0.00$ (Tracked in `declined_competency_ids`)
- **`UNCHANGED`:** $\Delta = 0.00$

### 16.2 Competency Gap Resolution Status
Each competency is evaluated against its baseline status:

| Baseline Status | Reassessment Outcome | Gap Resolution Status |
| :--- | :--- | :---: |
| **Had Skill Gap** | Reassessment Score &ge; 80.0% (`ADVANCED`) | **`RESOLVED`** |
| **Had Skill Gap** | Reassessment Score < 80.0%, but severity decreased (e.g., HIGH &rarr; MEDIUM) | **`REDUCED`** |
| **Had Skill Gap** | Reassessment Score < 80.0%, severity unchanged (e.g., HIGH &rarr; HIGH) | **`PERSISTENT`** |
| **Had Skill Gap** | Reassessment Score < 80.0%, severity increased (e.g., LOW &rarr; HIGH) | **`INCREASED`** |
| **No Baseline Gap** | Reassessment Score &ge; 80.0% | **`NO_GAP`** |
| **No Baseline Gap** | Reassessment Score < 80.0% (Candidate dropped below mastery) | **`NEW_GAP`** |

### 16.3 Macro Closed-Loop State Precedence
The platform determines an overall closed-loop status based on a strict 3-tier hierarchy:

$$\text{Loop State} = \begin{cases} 
\text{LOOP\_CLOSED} & \text{if } \forall g \in \text{Baseline Gaps}: \text{is\_resolved}(g) = \text{True} \\ 
\text{PARTIALLY\_CLOSED} & \text{if } \exists g \in \text{Baseline Gaps}: (\text{is\_resolved}(g) \lor \text{is\_reduced}(g)) \\ 
\text{LOOP\_OPEN} & \text{otherwise} 
\end{cases}$$

#### Strict Precedence Rules:
1. **`LOOP_CLOSED` (Highest Priority):** Every identified baseline skill gap achieved a reassessment score of &ge; 80.0% (`ADVANCED`). Zero unresolved baseline deficiencies remain.
2. **`PARTIALLY_CLOSED`:** At least one baseline gap was `RESOLVED` or `REDUCED`, while at least one baseline deficit remains unresolved.  
   *Note: A decline in another competency does NOT override `PARTIALLY_CLOSED`.*
3. **`LOOP_OPEN`:** Zero baseline skill gaps demonstrated improvement or reduction, or baseline deficits remain fully persistent.

---

## PART 17 — CLOSED LEARNING LOOP

### 17.1 Business Meaning of Macro States

#### Case 1: `LOOP_CLOSED`
- **Scenario:** Officer Ramesh had two baseline gaps: National Accounts (30%) and Sampling Design (60%).
- **Learning:** Ramesh completes both recommended iGOT modules.
- **Reassessment:** Ramesh scores 85% in National Accounts and 90% in Sampling Design.
- **Evaluation:** Both gaps are `RESOLVED`. Overall loop status: **`LOOP_CLOSED`**. The targeted capacity-building objective has been achieved.

#### Case 2: `PARTIALLY_CLOSED`
- **Scenario:** Officer Priya had two baseline gaps: Industrial Statistics (40%) and Survey Methodology (45%).
- **Learning:** Priya completes the Industrial Statistics module, but has not completed Survey Methodology.
- **Reassessment:** Priya scores 82% in Industrial Statistics (RESOLVED) and 45% in Survey Methodology (PERSISTENT).
- **Evaluation:** One gap resolved, one persists. Overall loop status: **`PARTIALLY_CLOSED`**. Leadership can see measurable progress while keeping the remaining deficit on the officer's learning pathway.

#### Case 3: `LOOP_OPEN`
- **Scenario:** Officer Suresh scored 40% in Index Numbers.
- **Reassessment:** After self-study without completing the course, Suresh retakes the exam and scores 42% (still <50%, HIGH gap).
- **Evaluation:** Gap remains `PERSISTENT`. Overall loop status: **`LOOP_OPEN`**. The intervention did not yield measurable proficiency improvement.

---

## PART 18 — LEARNING ACTIVITY CORRELATION

### 18.1 Associating Completed Learning with Reassessments
When generating a before/after comparison report, the backend queries the officer’s `recommendations` table for any course mapped to the evaluated competency that was `COMPLETED` or `STARTED` prior to the reassessment.

### 18.2 Non-Causal Educational Correlation Disclaimer
> [!NOTE]
> The backend explicitly reports learning activity as **educational context and developmental correlation, NOT formal scientific or causal proof**.

#### Implemented System Text:
In every comparison response (`app/services/reassessment_service.py`), the system includes the following standardized narrative:
```text
"Officer completed course '{course_title}' prior to reassessment. Competency score changed 
from {b_score}% to {r_score}% ({delta}%). This learning activity is documented as developmental 
context and educational correlation, not formal causal proof."
```
This language ensures academic rigor and prevents unwarranted claims of unconfounded causality.

---

## PART 19 — COMPLETE API REFERENCE

All endpoints are prefixed with `/api/v1` (configured via `settings.API_V1_PREFIX`).

### 19.1 Authentication & Profile (`/auth`)

#### 1. `POST /api/v1/auth/register`
- **Summary:** Register a new user account.
- **Auth / Role:** Public. `OFFICER`, `TRAINER`, and `SME` roles can be registered. Registration as `ADMIN` is strictly forbidden (HTTP 400).
- **Request Body:** `UserRegisterRequest` (`name`, `email`, `password`, `role`, `department`, `designation`).
- **Response:** `UserResponse` (`id`, `name`, `email`, `role`).
- **Errors:** 400 (Admin registration attempt / Invalid role), 409 (Email already registered).
- **DB Effects:** Inserts 1 row into `users`.

#### 2. `POST /api/v1/auth/login`
- **Summary:** Authenticate credentials and receive JWT access token.
- **Auth / Role:** Public.
- **Request Body:** `UserLoginRequest` (`email`, `password`).
- **Response:** `TokenResponse` (`access_token`, `token_type`: 'bearer', `user`: `UserResponse`).
- **Errors:** 401 (Invalid email or password), 403 (Account inactive).
- **DB Effects:** None (Read-only query on `users`).

#### 3. `POST /api/v1/auth/token`
- **Summary:** OAuth2 form-based authentication endpoint for Swagger UI.
- **Auth / Role:** Public. Accepts `application/x-www-form-urlencoded` (`username`, `password`).
- **Response:** `TokenResponse`.

#### 4. `GET /api/v1/auth/me`
- **Summary:** Retrieve profile of current authenticated user.
- **Auth / Role:** Authenticated (Any active role).
- **Response:** `UserMeResponse` (`id`, `name`, `email`, `role`, `department`, `designation`, `is_active`).

---

### 19.2 Documents Pipeline (`/documents`)

#### 5. `POST /api/v1/documents`
- **Summary:** Upload and ingest learning materials (PDF/PPTX).
- **Auth / Role:** `TRAINER`, `ADMIN`.
- **Request Body:** `multipart/form-data` (`file: UploadFile`).
- **Response:** `DocumentResponse` (`id`, `filename`, `file_type`, `status`, `uploaded_by`, `created_at`).
- **Errors:** 400 (Unsupported file extension), 413 (File exceeds 20MB limit), 500 (Processing failure).
- **DB Effects:** Inserts 1 row into `documents`, inserts $N$ rows into `document_chunks`. Indexes $N$ vectors into ChromaDB.

#### 6. `GET /api/v1/documents`
- **Summary:** List uploaded documents with pagination.
- **Auth / Role:** Authenticated (Any role).
- **Query Params:** `skip` (default 0), `limit` (default 100).
- **Response:** `List[DocumentResponse]`.

#### 7. `GET /api/v1/documents/{document_id}`
- **Summary:** Retrieve document metadata and chunk count.
- **Auth / Role:** Authenticated (Any role).
- **Response:** `DocumentDetailResponse` (Includes `chunk_count` without exposing filesystem path).

#### 8. `DELETE /api/v1/documents/{document_id}`
- **Summary:** Delete document, associated chunks, vector embeddings, and physical file.
- **Auth / Role:** Uploader of the document or `ADMIN`.
- **Errors:** 400 (Cannot delete if questions are linked to document), 403 (Forbidden), 404 (Not found).
- **DB Effects:** Deletes row from `documents` (cascades to `document_chunks`). Deletes vectors from ChromaDB.

#### 9. `POST /api/v1/documents/search`
- **Summary:** Semantic similarity search across indexed chunks.
- **Auth / Role:** Authenticated (Any role).
- **Request Body:** `DocumentSearchRequest` (`query`, `top_k`, optional `document_id`).
- **Response:** `List[DocumentSearchResult]`.

---

### 19.3 Question Bank & SME Review (`/questions`)

#### 10. `POST /api/v1/questions/generate`
- **Summary:** Generate grounded MCQs from a processed document using Mistral AI RAG.
- **Auth / Role:** `TRAINER`, `ADMIN`.
- **Request Body:** `QuestionGenerateRequest` (`document_id`, optional `competency_id`, `num_questions`: 1–20, `difficulty`).
- **Response:** `List[QuestionResponse]`.
- **Errors:** 400 (Document not PROCESSED), 404 (Document/competency not found), 502 (AI generation failed quality checks).
- **DB Effects:** Inserts $K$ rows into `questions` with status `PENDING_REVIEW`. Increments `documents.generation_count`.

#### 11. `GET /api/v1/questions`
- **Summary:** List questions with filtering and pagination.
- **Auth / Role:** `TRAINER`, `SME`, `ADMIN`.
- **Query Params:** `document_id`, `status` (`PENDING_REVIEW`, `APPROVED`, `REJECTED`), `competency_id`, `difficulty`, `skip`, `limit`.
- **Response:** `QuestionListResponse` (`total`, `items`).

#### 12. `GET /api/v1/questions/{question_id}`
- **Summary:** Retrieve full question detail by ID.
- **Auth / Role:** `TRAINER`, `SME`, `ADMIN`.
- **Response:** `QuestionResponse`.

#### 13. `POST /api/v1/questions/{question_id}/review`
- **Summary:** Record SME audit decision (`APPROVE` or `REJECT`) for a pending MCQ.
- **Auth / Role:** `SME`, `ADMIN`.
- **Request Body:** `QuestionReviewRequest` (`action`: APPROVE/REJECT, optional `comment`).
- **Response:** `QuestionReviewResponse` (`id`, `question_id`, `action`, `comment`, `question_status`, `created_at`).
- **Errors:** 400 (Question not in PENDING_REVIEW), 404 (Question not found).
- **DB Effects:** Updates `questions.status`. Inserts 1 row into `question_reviews`.

---

### 19.4 Assessments & Reassessments (`/assessments`)

#### 14. `POST /api/v1/assessments`
- **Summary:** Create a diagnostic assessment with approved competency questions.
- **Auth / Role:** `OFFICER` (self), `ADMIN` (can specify `officer_id`). `TRAINER` and `SME` receive 403 Forbidden.
- **Request Body:** `AssessmentCreateRequest` (optional `title`, optional `officer_id`, `question_count`: 1–50, optional `competency_id`, optional `document_id`).
- **Response:** `AssessmentResponse` (`id`, `officer_id`, `title`, `status`: IN_PROGRESS, `total_questions`, `score_percentage`: 0.00).
- **Errors:** 400 (Insufficient approved questions), 404 (Competency/document not found).
- **DB Effects:** Inserts 1 row into `assessments`. Inserts $N$ rows into `assessment_questions`.

#### 15. `GET /api/v1/assessments`
- **Summary:** List assessments with ownership filtering.
- **Auth / Role:** `OFFICER` (sees own only), `TRAINER` & `ADMIN` (see all). `SME` receives 403 Forbidden.
- **Query Params:** `status` (IN_PROGRESS/COMPLETED), `skip`, `limit`.
- **Response:** `AssessmentListResponse` (`total`, `items`).

#### 16. `GET /api/v1/assessments/{assessment_id}`
- **Summary:** Retrieve assessment questions with safe exam masking.
- **Auth / Role:** `OFFICER` (own only), `TRAINER`, `ADMIN`.
- **Response:** `AssessmentDetailResponse` (`questions`: options visible, answer keys/explanations masked).

#### 17. `POST /api/v1/assessments/{assessment_id}/submit`
- **Summary:** Atomically evaluate submitted answers, compute scores, and persist competency results and skill gaps.
- **Auth / Role:** Assigned `OFFICER` (own only) or `ADMIN`.
- **Request Body:** `AssessmentSubmitRequest` (`answers`: `List[{question_id, selected_option}]`).
- **Response:** `AssessmentResultResponse` (Full unmasked evaluation, competency scores, skill gaps).
- **Errors:** 400 (Already completed, empty submission, missing questions, unassigned questions).
- **DB Effects:** Inserts $N$ rows into `answers`, inserts $C$ rows into `competency_results`, inserts $G$ rows into `skill_gaps`, updates `assessments` to `COMPLETED`. Hooks recommendation generation.

#### 18. `GET /api/v1/assessments/{assessment_id}/result`
- **Summary:** Retrieve evaluation outcome and unmasked questions for a completed assessment.
- **Auth / Role:** Assigned `OFFICER` (own only), `TRAINER`, `ADMIN`.
- **Errors:** 400 (Assessment still IN_PROGRESS).

#### 19. `POST /api/v1/assessments/{baseline_id}/reassess`
- **Summary:** Initiate a targeted reassessment linked to a completed baseline assessment.
- **Auth / Role:** Assigned `OFFICER` (own baseline only) or `ADMIN`.
- **Request Body:** Optional `ReassessmentCreateRequest` (optional `title`, optional `question_count`, optional `competency_ids`).
- **Response:** `AssessmentDetailResponse` (Safe exam view with canonical title linkage).
- **Errors:** 400 (Baseline not COMPLETED, attempting to reassess a reassessment, no gaps to reassess).
- **DB Effects:** Inserts 1 row into `assessments` with canonical title, inserts $M$ rows into `assessment_questions`.

#### 20. `GET /api/v1/assessments/{reassessment_id}/comparison`
- **Summary:** Generate before-vs-after comparison evaluating the closed learning loop.
- **Auth / Role:** Assigned `OFFICER` (own only), `TRAINER`, `ADMIN`.
- **Query Params:** Optional `baseline_id` (must match title linkage if supplied).
- **Response:** `ReassessmentComparisonResponse` (Overall delta, macro loop status, competency comparisons, associated learning with non-causal disclaimer).
- **Errors:** 400 (Reassessment in progress, self-comparison, mismatched baseline query param).

#### 21. `GET /api/v1/assessments/{baseline_id}/reassessments`
- **Summary:** List sequential reassessment attempts linked to a baseline assessment.
- **Auth / Role:** Assigned `OFFICER` (own only), `TRAINER`, `ADMIN`.
- **Response:** `ReassessmentListResponse` (`baseline_assessment_id`, `total_attempts`, `items`).

---

### 19.5 Courses Catalogue (`/courses`)

#### 22. `GET /api/v1/courses`
- **Summary:** Browse active courses in the iGOT-aligned catalogue.
- **Auth / Role:** Authenticated (`OFFICER`, `TRAINER`, `ADMIN`, `SME`).
- **Query Params:** `query`, `competency_id`, `difficulty`, `language`, `skip`, `limit`.
- **Response:** `CourseListResponse` (`total`, `items`).

#### 23. `GET /api/v1/courses/{course_id}`
- **Summary:** Retrieve full course details and mapped competencies.
- **Auth / Role:** Authenticated (`OFFICER`, `TRAINER`, `ADMIN`, `SME`).
- **Response:** `CourseDetailResponse` (Includes `competencies` with `relevance_score`).

---

### 19.6 Recommendations Engine (`/recommendations` & `/assessments/{id}/recommendations`)

#### 24. `POST /api/v1/assessments/{assessment_id}/recommendations`
- **Summary:** Generate or regenerate recommendations for a completed assessment.
- **Auth / Role:** Assigned `OFFICER` (own only) or `ADMIN`. `TRAINER` and `SME` receive 403 Forbidden.
- **Response:** `List[RecommendationResponse]`.
- **Errors:** 400 (Assessment not COMPLETED).
- **DB Effects:** Inserts/refreshes rows in `recommendations`, preserving historical learning states.

#### 25. `GET /api/v1/assessments/{assessment_id}/recommendations`
- **Summary:** List recommendations linked to a specific assessment.
- **Auth / Role:** Assigned `OFFICER` (own only), `TRAINER`, `ADMIN`.

#### 26. `GET /api/v1/recommendations`
- **Summary:** List recommendations across assessments with filtering and pagination.
- **Auth / Role:** `OFFICER` (own only), `TRAINER`, `ADMIN`.
- **Query Params:** `assessment_id`, `status` (`RECOMMENDED`, `STARTED`, `COMPLETED`, `DISMISSED`), `skip`, `limit`.
- **Response:** `RecommendationListResponse` (`total`, `items`).

#### 27. `GET /api/v1/recommendations/{recommendation_id}`
- **Summary:** Retrieve details of a single recommendation.
- **Auth / Role:** Assigned `OFFICER` (own only), `TRAINER`, `ADMIN`.
- **Response:** `RecommendationResponse`.

#### 28. `PATCH /api/v1/recommendations/{recommendation_id}/status`
- **Summary:** Advance recommendation status along the strict state machine.
- **Auth / Role:** Assigned `OFFICER` (own only) or `ADMIN`.
- **Request Body:** `RecommendationStatusUpdateRequest` (`status`: STARTED, COMPLETED, DISMISSED).
- **Response:** `RecommendationResponse`.
- **Errors:** 400 (Invalid state transition), 403 (Unauthorized officer/role).
- **DB Effects:** Updates `recommendations.status`.

---

## PART 20 — COMPLETE END-TO-END DATA TRACE

This section traces a fictional Indian Statistical Service officer, **Officer Ramesh Kumar** (`officer_id: 101`), through the complete closed-loop lifecycle.

```text
========================================================================================================================
STEP 1: LOGIN & AUTHENTICATION
========================================================================================================================
- Action: Ramesh logs in.
- API Called: POST /api/v1/auth/login
  Body: {"email": "ramesh.kumar@mospi.gov.in", "password": "[REDACTED]"}
- Service Responsible: AuthService.authenticate_user()
- Database Effect:
  * SELECT FROM users WHERE email = 'ramesh.kumar@mospi.gov.in';
  * Argon2id verifies password hash against database record.
- Output: JWT access token issued encoding {"sub": "101", "role": "OFFICER"}.

========================================================================================================================
STEP 2: DIAGNOSTIC BASELINE ASSESSMENT CREATION
========================================================================================================================
- Action: Ramesh starts a diagnostic assessment in Economic Statistics.
- API Called: POST /api/v1/assessments
  Headers: Authorization: Bearer <token>
  Body: {"title": "MoSPI Baseline Diagnostic 2026", "question_count": 4}
- Service Responsible: AssessmentService.create_assessment()
- Database Effect:
  * Queries Question for status='APPROVED' and competency_id IS NOT NULL ORDER BY id ASC LIMIT 4.
    Selected: Question #201 (ASI Methodology), #202 (ASI Methodology), #203 (IIP Index), #204 (IIP Index).
  * INSERT INTO assessments (officer_id=101, title='MoSPI Baseline Diagnostic 2026', status='IN_PROGRESS',
                             total_questions=4, total_correct=0, score_percentage=0.00) RETURNING id=501;
  * INSERT INTO assessment_questions:
    (assessment_id=501, question_id=201, order=1), (assessment_id=501, question_id=202, order=2),
    (assessment_id=501, question_id=203, order=3), (assessment_id=501, question_id=204, order=4);
  * Commit.
- Output: Assessment #501 created with status IN_PROGRESS.

========================================================================================================================
STEP 3: EXAM RETRIEVAL & ANSWER SUBMISSION
========================================================================================================================
- Action: Ramesh loads the exam, answers all 4 questions, and submits.
- API Called: POST /api/v1/assessments/501/submit
  Body: {
    "answers": [
      {"question_id": 201, "selected_option": "B"},  // Incorrect (Correct is A)
      {"question_id": 202, "selected_option": "C"},  // Incorrect (Correct is D)
      {"question_id": 203, "selected_option": "A"},  // Correct (Correct is A)
      {"question_id": 204, "selected_option": "B"}   // Correct (Correct is B)
    ]
  }
- Service Responsible: AssessmentService.submit_assessment()
- Database Effect (Single Atomic Transaction):
  * INSERT INTO answers (4 rows inserted with evaluated is_correct values).
  * Overall score computed: 2 correct out of 4 = 50.00%.
  * UPDATE assessments SET status='COMPLETED', total_correct=2, score_percentage=50.00, completed_at=NOW() WHERE id=501;
  * Competency scoring:
    - Competency #57 (ASI Methodology): 0/2 correct = 0.00% -> BEGINNER
    - Competency #122 (IIP Index): 2/2 correct = 100.00% -> ADVANCED
  * INSERT INTO competency_results:
    (assessment_id=501, competency_id=57, attempted=2, correct=0, score=0.00, proficiency='BEGINNER'),
    (assessment_id=501, competency_id=122, attempted=2, correct=2, score=100.00, proficiency='ADVANCED');
  * Skill gap identification:
    - Competency #57 (0.00% < 50.0%) -> HIGH skill gap generated.
    - Competency #122 (100.00% >= 80.0%) -> No skill gap.
  * INSERT INTO skill_gaps:
    (assessment_id=501, competency_id=57, score_percentage=0.00, gap_level='HIGH');
  * Transaction commits.
  * Recommendation hook triggers RecommendationService.generate_recommendations(assessment_id=501).
- Automatic Recommendation Engine Effect:
  * Identifies HIGH gap in Competency #57.
  * Matches Course #93 ("Annual Survey of Industries (ASI): Frame, Concepts & Sampling") with relevance 0.95.
  * Match score: 0.95 * 1.00 * 100 = 95.00%. Priority: 1.
  * INSERT INTO recommendations:
    (officer_id=101, assessment_id=501, competency_id=57, course_id=93, priority=1, match_score=95.00,
     status='RECOMMENDED', reason='Recommended because your assessment score in ASI Survey Methodology was 0.0%...');

========================================================================================================================
STEP 4: ENGAGING WITH RECOMMENDED LEARNING
========================================================================================================================
- Action: Ramesh begins studying Course #93 and transitions its status.
- API Called: PATCH /api/v1/recommendations/{rec_id}/status
  Body: {"status": "STARTED"}
- Database Effect: UPDATE recommendations SET status='STARTED' WHERE id={rec_id};
- Action: Upon completing the training module, Ramesh records completion.
- API Called: PATCH /api/v1/recommendations/{rec_id}/status
  Body: {"status": "COMPLETED"}
- Database Effect: UPDATE recommendations SET status='COMPLETED' WHERE id={rec_id};

========================================================================================================================
STEP 5: TARGETED POST-LEARNING REASSESSMENT
========================================================================================================================
- Action: Ramesh triggers reassessment for his completed baseline assessment #501.
- API Called: POST /api/v1/assessments/501/reassess
  Body: {"title": "Targeted Reassessment"}
- Service Responsible: ReassessmentService.create_reassessment()
- Database Effect:
  * Identifies baseline gap in Competency #57.
  * Queries Question for status='APPROVED' and competency_id=57 ORDER BY id ASC.
    Selected: Question #201, #202.
  * Formats canonical title: "Reassessment [Baseline #501]: Targeted Reassessment".
  * INSERT INTO assessments (officer_id=101, title='Reassessment [Baseline #501]: Targeted Reassessment',
                             status='IN_PROGRESS', total_questions=2) RETURNING id=502;
  * INSERT INTO assessment_questions:
    (assessment_id=502, question_id=201, order=1), (assessment_id=502, question_id=202, order=2);
  * Commit.
- Output: Reassessment #502 initialized in IN_PROGRESS state.

========================================================================================================================
STEP 6: REASSESSMENT SUBMISSION & EVALUATION
========================================================================================================================
- Action: Ramesh answers the targeted questions correctly after learning and submits.
- API Called: POST /api/v1/assessments/502/submit
  Body: {
    "answers": [
      {"question_id": 201, "selected_option": "A"},  // Correct!
      {"question_id": 202, "selected_option": "D"}   // Correct!
    ]
  }
- Service Responsible: AssessmentService.submit_assessment()
- Database Effect:
  * Answers evaluated: 2/2 correct = 100.00%.
  * UPDATE assessments SET status='COMPLETED', total_correct=2, score_percentage=100.00 WHERE id=502;
  * INSERT INTO competency_results (assessment_id=502, competency_id=57, score=100.00, proficiency='ADVANCED');
  * Baseline Assessment #501 remains 100% UNCHANGED.

========================================================================================================================
STEP 7: CLOSED LEARNING LOOP EVALUATION & COMPARISON
========================================================================================================================
- Action: Officer/Trainer inspects the longitudinal comparison report.
- API Called: GET /api/v1/assessments/502/comparison
- Service Responsible: ReassessmentService.get_reassessment_comparison()
- Mathematical Evaluation:
  * Baseline Score: 0.00% | Reassessment Score: 100.00% | Delta: +100.00% (IMPROVED)
  * Competency #57 reached 100.00% (>= 80.0%) -> RESOLVED
  * All baseline gaps resolved -> Macro Status: LOOP_CLOSED
  * Associated Learning: Course #93 (COMPLETED) with educational attribution disclaimer.
- Output: ReassessmentComparisonResponse returned. Closed learning loop mathematically verified and closed!
```

---

## PART 21 — ACTUAL DATA / SEED DATA

### 21.1 Live Database Counts
Inspected directly from the live PostgreSQL database (`statkarmayogi_db`):

| Table Name | Live Row Count | Primary Source / Origin |
| :--- | :---: | :--- |
| `roles` | **4** | Core System Seed (`seed_roles`) |
| `users` | **2,541** | Seed & System Verification Test Accounts |
| `competencies` | **159** | MoSPI Competency Framework Reference Seed |
| `courses` | **95** | Curated iGOT Prototype Modules & Test Fixtures |
| `course_competencies` | **74** | Curated Relevance Bridge Mappings |
| `documents` | **924** | Test Ingested PDF & Presentation Manuals |
| `document_chunks` | **1,340** | Parsed & Split Relational Text Segments |
| `questions` | **744** | RAG Generated & Seeded Question Bank |
| `question_reviews` | **117** | SME Review Audit Records |
| `assessments` | **545** | Baseline Examinations & Longitudinal Reassessments |
| `assessment_questions` | **1,162** | Assessment Manifest Join Rows |
| `answers` | **318** | Evaluated Question Submissions |
| `competency_results` | **226** | Computed Competency Profile Results |
| `skill_gaps` | **154** | Identified Competency Deficits (< 80%) |
| `recommendations` | **116** | Generated Course Pathways across States |
| `alembic_version` | **1** | Alembic Migration Version Record |

### 21.2 The 4 System Roles
- `TRAINER` (ID: 1): Curriculum development, document upload, and MCQ generation.
- `SME` (ID: 2): Subject matter review, quality auditing, question approval/rejection.
- `OFFICER` (ID: 3): Target statistical officers; takes exams, engages in training, requests reassessments.
- `ADMIN` (ID: 4): System oversight, user governance, unrestricted diagnostic access.

---

## PART 22 — WHAT IS REAL VS MOCK VS DETERMINISTIC VS AI

To maintain total transparency during technical demonstrations and Smart India Hackathon judging, every subsystem is classified below:

| System Subsystem | Classification | Technical Explanation |
| :--- | :---: | :--- |
| **User & RBAC Model** | **REAL DATABASE DATA** | Fully implemented in PostgreSQL with real Argon2id password hashing, real JWT authentication, and enforced database relationships. |
| **PostgreSQL Schema (16 Tables)** | **REAL DATABASE DATA** | Real, ACID-compliant relational tables managed in PostgreSQL with foreign keys and cascading deletes. |
| **Document Ingestion & Chunking** | **REAL / DETERMINISTIC** | Real file uploads (PDF/PPTX) streamed to disk, parsed via LangChain, and split into real text chunks. |
| **Vector Store & Embeddings** | **REAL EXTERNAL API** | Real Mistral AI embeddings (`mistral-embed`) stored locally in real ChromaDB collections. |
| **MCQ Question Generation** | **AI / LLM GENERATED** | Real calls to Mistral Large (`mistral-large-latest`) with structured Pydantic schema enforcement. |
| **SME Question Review** | **USER GENERATED** | Real human-in-the-loop workflow recording immutable audit rows in PostgreSQL. |
| **Assessment Delivery & Masking** | **DETERMINISTIC LOGIC** | Pure deterministic Python logic masking answer keys and Citations during exam execution. |
| **Assessment Scoring Engine** | **DETERMINISTIC LOGIC** | Pure deterministic arithmetic calculating percentage scores and mapping proficiency tiers. |
| **Skill Gap Identification** | **DETERMINISTIC LOGIC** | Strict deterministic thresholds (High < 50%, Medium < 65%, Low < 80%, Mastery &ge; 80%). |
| **iGOT Course Catalogue** | **PROTOTYPE / CURATED DATA** | Curated reference courses representing official MoSPI training modules. Stored in real PostgreSQL tables. |
| **iGOT External API Integration** | **MOCK INTEGRATION** | `MockIGOTAdapter` abstracts the external discovery boundary. **Zero live calls to DoPT/iGOT servers.** |
| **Recommendation Matching** | **DETERMINISTIC LOGIC** | 100% deterministic mathematical formula (`relevance * gap_multiplier * 100`). No black-box AI models. |
| **Recommendation State Machine** | **DETERMINISTIC LOGIC** | Strict deterministic state transitions (`RECOMMENDED` &rarr; `STARTED` &rarr; `COMPLETED`). |
| **Reassessment Linkage** | **DETERMINISTIC LOGIC** | Pure deterministic regular expression parsing and title-based canonical linkage. |
| **Before / After Comparison** | **DETERMINISTIC LOGIC** | Deterministic delta calculations and 3-tier macro closed-loop state precedence evaluation. |
| **Educational Correlation** | **DETERMINISTIC DISCLOSURE** | Explicit educational disclaimer stating correlation rather than scientific causality. |

---

## PART 23 — TRANSACTION AND DATA INTEGRITY

### 23.1 Atomic Assessment Submission
Assessment submission (`AssessmentService.submit_assessment`) executes inside a single atomic database transaction:
- The answers are evaluated and inserted.
- Pre-existing `competency_results` and `skill_gaps` for that assessment ID are deleted (idempotency guard).
- Aggregated scores and proficiency levels are calculated and inserted.
- Skill gaps are identified and inserted.
- Assessment status is transitioned to `COMPLETED`.
- If any database operation fails, the transaction issues `db.rollback()`. No partial or corrupted assessment results can ever exist in PostgreSQL.

### 23.2 Safe Recommendation Hook Isolation
Following a successful commit of an assessment submission, the system triggers `RecommendationService.generate_recommendations` within an isolated `try...except` block:
```python
try:
    RecommendationService.generate_recommendations(db=db, assessment_id=assessment.id, current_user=current_user)
except Exception as rec_err:
    logger.error(f"Automatic recommendation generation failed: {rec_err}")
    # Intentionally isolated: Assessment remains COMPLETED!
```
**Architectural Rationale:** If recommendation matching encounters an unexpected issue (e.g., catalogue unavailability), the candidate’s completed examination and score remain 100% safe, committed, and intact. The officer or administrator can regenerate recommendations at any time via `POST /api/v1/assessments/{id}/recommendations`.

---

## PART 24 — ERROR HANDLING

The backend enforces strict standard HTTP error responses with clean, actionable details:

| Status Code | Primary Cause | API Error Response | Database State |
| :---: | :--- | :--- | :--- |
| **400** | Assessment already completed | `"Assessment has already been completed and cannot be resubmitted."` | Unchanged |
| **400** | Incomplete answer submission | `"All assigned assessment questions must be answered before submission."` | Unchanged |
| **400** | Reassessing a reassessment | `"Cannot create a reassessment of another reassessment. Target must be an original baseline assessment."` | Unchanged |
| **400** | Self-comparison attempt | `"Cannot compare an assessment against itself."` | Unchanged |
| **400** | Invalid recommendation status | `"Invalid status transition from COMPLETED to STARTED."` | Unchanged |
| **401** | Missing / Expired JWT Token | `"Token has expired. Please log in again."` or `"Could not validate credentials."` | Unchanged |
| **403** | Unauthorized role operation | `"Operation not permitted. Required role: TRAINER, ADMIN"` | Unchanged |
| **403** | Cross-officer data access | `"Access denied. You can only view your own assessments."` | Unchanged |
| **403** | SME accessing exams | `"Access denied. SME role cannot inspect assessments."` | Unchanged |
| **404** | Resource not found | `"Assessment with ID 9999 not found."` | Unchanged |
| **409** | Duplicate registration email | `"An account with this email address already exists."` | Unchanged |
| **413** | File upload exceeds 20MB | `"File exceeds maximum allowed size of 20MB."` | Cleaned from storage |

---

## PART 25 — TESTING AND VERIFICATION

### 25.1 Test Suite Structure (174 Passed)
The automated test suite in `backend/tests/` contains **exactly 174 tests across 9 test files**, all passing with zero regressions:

```text
tests/test_assessments.py ............................                   [ 16%] (28 tests)
tests/test_auth.py .............................                         [ 32%] (29 tests)
tests/test_courses.py ........                                           [ 37%] ( 8 tests)
tests/test_documents.py ........................                         [ 51%] (24 tests)
tests/test_health.py .....                                               [ 54%] ( 5 tests)
tests/test_models.py ..........                                          [ 59%] (10 tests)
tests/test_questions.py .............................                    [ 76%] (29 tests)
tests/test_reassessments.py .....................                        [ 88%] (21 tests)
tests/test_recommendations.py ....................                       [100%] (20 tests)
================================= 174 passed in 20.29s =================================
```

### 25.2 Live PostgreSQL Verification Script
In addition to unit and integration test fixtures, the backend includes an end-to-end live PostgreSQL verification harness (`scratch/verify_phase_9_reassessment.py`). This script executes a complete real-world walkthrough against the live database:
- Confirms strictly 16 PostgreSQL tables with zero schema alterations.
- Tests real user creation, token generation, baseline diagnostic execution, recommendation generation, recommendation state machine progression, targeted reassessment creation, reassessment grading, baseline immutability verification, before/after comparison math, and closed-loop macro state evaluation.
- All 14 live verification checks pass successfully.

---

## PART 26 — DATABASE AND BACKEND INVARIANTS ("DO NOT BREAK")

To preserve system integrity, future developers must strictly respect the following core invariants:

1. **Zero Schema Changes:** Maintain strictly the existing 16 tables. Do not add columns (such as `is_external`, `baseline_id`, or `reassessment_flag`) to existing tables.
2. **Canonical Title-Based Linkage:** Reassessments must continue to encode baseline linkages in their title: `Reassessment [Baseline #{id}]: {title}`.
3. **Baseline Immutability:** Baseline assessments, once completed, are strictly immutable. No reassessment operation may alter baseline rows, scores, or skill gaps.
4. **Active Recommendation Cap:** The global active recommendation cap of 6 (`MAX_TOTAL_ACTIVE_RECOMMENDATIONS`) applies **only to active recommendations**. Historical records (`STARTED`, `COMPLETED`, `DISMISSED`) must never be pruned.
5. **No Fake Competency Mappings:** If an iGOT course lacks an established, verified competency in the database, it **must remain unmapped**. Never fabricate artificial mappings or apply arbitrary fallback competencies.
6. **Masking During Examination:** Under no circumstances should `Question.correct_option`, `Question.explanation`, `Question.source_page`, or `Question.source_chunk_id` be exposed while an assessment is `IN_PROGRESS`.
7. **80% Mastery Benchmark:** The 80.0% threshold (`ADVANCED`) is the authoritative boundary for skill gap generation and gap resolution. Do not alter this threshold without formal MoSPI policy authorization.
8. **RBAC Isolation:** The SME role must remain strictly isolated to content review. SMEs must never be permitted to take assessments, submit answers, view officer results, or inspect recommendations.

---

## PART 27 — DEBUGGING GUIDE

### Scenario 1: Recommendations are missing after completing an assessment
1. **Check Skill Gaps:** Inspect `SELECT * FROM skill_gaps WHERE assessment_id = <id>;`. If the candidate achieved &ge; 80% in all competencies, zero skill gaps exist, and zero recommendations are expected.
2. **Check Course Mappings:** Inspect `course_competencies` for the deficient competency ID:  
   `SELECT * FROM course_competencies WHERE competency_id = <id>;`. If no active courses are mapped to that competency, no candidates can be matched.
3. **Check Manual Regeneration:** Trigger `POST /api/v1/assessments/{id}/recommendations` and check backend console logs for specific warnings.

### Scenario 2: Reassessment creation fails with HTTP 400 Bad Request
1. **Check Baseline Status:** Verify `SELECT status, title FROM assessments WHERE id = <id>;`. The baseline must have `status = 'COMPLETED'`.
2. **Check for Reassessing a Reassessment:** If the baseline title starts with `Reassessment [Baseline #`, it is already a reassessment. Reassessments can only target original baseline assessments.
3. **Check Question Bank:** Ensure approved questions exist for the deficient competencies:  
   `SELECT count(*) FROM questions WHERE competency_id IN (...) AND status = 'APPROVED';`.

### Scenario 3: Closed loop status is `PARTIALLY_CLOSED` instead of `LOOP_CLOSED`
1. **Inspect Competency Scores:** Check if *every* baseline gap reached &ge; 80.0%:  
   `SELECT competency_id, score_percentage FROM competency_results WHERE assessment_id = <reassessment_id>;`.
2. If even one baseline deficit scored 79.99%, it is classified as `REDUCED` or `PERSISTENT`, keeping the macro loop at `PARTIALLY_CLOSED`.

---

## PART 28 — COMMON MISUNDERSTANDINGS

1. **iGOT Adapter $\ne$ Live External Web Scraping:** The adapter is an internal architectural abstraction that models iGOT integration. It does not initiate network sessions to external government servers.
2. **Prototype Course $\ne$ Live Government Portal Module:** The six courses are curated reference modules demonstrating competency alignment. They are not live government enrollments.
3. **Recommendation $\ne$ Mandatory Enrollment:** A recommendation is an adaptive learning suggestion based on diagnostic gaps; it does not force an officer into an administrative course cohort.
4. **Competency $\ne$ Skill Gap:** A `Competency` is a standardized domain capability (e.g., Sampling Design). A `SkillGap` is an officer's specific diagnostic deficit (< 80%) in that capability.
5. **Reassessment Improvement $\ne$ Scientific Causal Proof:** Higher scores on a reassessment reflect positive educational development correlated with completed learning modules, but do not constitute formal, randomized causal proof.
6. **Active Recommendation Limit $\ne$ Historical Limit:** The limit of 6 applies strictly to *unstarted, active recommendations*. Historical rows (`COMPLETED`, `DISMISSED`) are preserved indefinitely.

---

## PART 29 — SECURITY / DATA SAFETY NOTES

- **No Plaintext Passwords:** Passwords are never stored in plaintext or logged. All passwords are encrypted with Argon2id.
- **JWT Key Isolation:** The JWT signing key is read from the `JWT_SECRET_KEY` environment variable. Never hardcode production secrets in source code.
- **Input Sanitization:** Uploaded filenames are sanitized with regular expressions (`re.sub(r"[^\w\.\-]", "_", filename)`) to prevent path traversal vulnerabilities.
- **File Storage Safety:** Uploaded documents are saved under randomly generated UUID prefixes (`{uuid}_{sanitized_name}`) to prevent filename collisions and overwrite attacks.
- **Masked Exam Keys:** Correct answer choices and citations are stripped at the database query layer for any assessment that is not yet completed.

---

## PART 30 — CURRENT LIMITATIONS

1. **Local Prototype Boundary:** External iGOT course synchronization and live candidate single-sign-on (SSO) via Parichay/Jan Parichay are not implemented in this prototype.
2. **Local Vector Storage:** ChromaDB runs in embedded persistent mode on the local server filesystem rather than as a distributed cluster.
3. **Document Formats:** Ingestion currently supports PDF and presentation files (`.pdf`, `.pptx`, `.ppt`). Scanned image-only PDFs without OCR text layers are not currently processed.
4. **Static Question Bank:** MCQ generation requires a prior document ingestion step. Questions are not generated dynamically on-the-fly during an active examination.

---

## PART 31 — FUTURE EXTENSIONS

*(The following capabilities are logical future enhancements and are **NOT** currently implemented in the codebase)*:
- **Jan Parichay / Parichay National SSO Integration:** Government employee single-sign-on authentication.
- **Live iGOT Karmayogi API Webhook Sync:** Real-time bi-directional synchronization of course progress and completion certificates from the official DoPT iGOT platform.
- **OCR Ingestion Pipeline:** Integration of Tesseract or Google Cloud Vision for scanned archival MoSPI survey documents.
- **Adaptive Item Response Theory (IRT):** Dynamically adjusting question difficulty during an examination based on real-time candidate response accuracy.
- **Departmental Analytics Dashboard:** Aggregated macro dashboards for Joint Directors and Division Heads to visualize regional competency heatmaps across India.

---

## PART 32 — FINAL SYSTEM SUMMARY

### Executive Summary for Non-Technical Stakeholders
StatKarmayogi transforms civil service training from passive, unmeasured course consumption into a **measurable, data-driven closed learning loop**:

```text
+-------------------+      Diagnostic Exam       +-------------------+
|  1. ASSESS        | -------------------------> |  2. IDENTIFY GAPS |
|  Officer takes    |                            |  Deficits (< 80%) |
|  diagnostic test  |                            |  isolated by domain
+-------------------+                            +-------------------+
                                                           │
                                                           │ Adaptive match
                                                           ▼
+-------------------+      Targeted Exam         +-------------------+
|  4. REASSESS      | <------------------------- |  3. LEARN         |
|  Longitudinal     |                            |  Officer consumes |
|  delta verified   |                            |  recommended iGOT |
+-------------------+                            |  modules          |
                                                 +-------------------+
```

- **What Goes In:** Official MoSPI manuals and training documents are ingested. Officers take diagnostic assessments covering core statistical competencies.
- **What Happens:** The system deterministically identifies competency deficiencies (< 80%), matches those gaps to relevant iGOT courses using transparent, explainable formulas, and records training progress.
- **What Comes Out:** Upon completing learning, officers undergo targeted reassessments. The system produces longitudinal before-and-after comparison reports mathematically verifying whether the competency gap has been resolved (`LOOP_CLOSED`).
- **Why It Matters:** For the first time, MoSPI leadership can objectively demonstrate the concrete return on capacity-building investments across the Indian Statistical Service.

---
*End of Authoritative Technical Report — StatKarmayogi Database & Backend Master Guide*
