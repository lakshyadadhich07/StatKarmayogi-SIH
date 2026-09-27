# StatKarmayogi — Phase 6 Implementation Report
## SME Question Review, Approval & Rejection Workflow

**Smart India Hackathon 2026**  
- **Problem Statement ID**: SIH26101  
- **Organization**: Ministry of Statistics and Programme Implementation (MoSPI)  
- **Theme**: Smart Education  
- **Phase**: Phase 6 — Human-in-the-Loop SME Question Review  
- **Status**: Completed & Fully Verified  

---

## 1. Executive Summary

Phase 6 implements the **Human-in-the-Loop (HITL) Quality Gate** for StatKarmayogi. While Phase 5 uses Retrieval-Augmented Generation (RAG) with Mistral AI to draft grounded Multiple Choice Questions (MCQs) from MoSPI reference manuals, no AI-generated question is ever served directly to civil servants or trainees without explicit human Subject Matter Expert (SME) validation.

Phase 6 delivers an auditable review and approval workflow:
- Only authorized Subject Matter Experts (`SME`) and MoSPI Administrators (`ADMIN`) can review pending questions.
- Reviews enforce strict state transition rules: only questions in `PENDING_REVIEW` status can be evaluated.
- Review decisions (`APPROVE` or `REJECT`) along with optional SME comments/critiques are recorded in the existing PostgreSQL `question_reviews` audit table.
- Question status updates (`APPROVED` or `REJECTED`) and review audit creation execute in a **single atomic database transaction** with rollback safety.
- **Zero database schema modifications** were required; existing tables and PostgreSQL enums from Phase 2 were 100% sufficient.

---

## 2. Files Modified & Created

### Modified Files:
1. `app/schemas/question.py`: Added Pydantic v2 schemas:
   - `QuestionReviewRequest`: Validates `action` (`ReviewAction.APPROVE` | `ReviewAction.REJECT`) and optional `comment: Optional[str]`.
   - `QuestionReviewResponse`: Response model returning `id`, `question_id`, `reviewer_id`, `action`, `comment`, `created_at`, `question_status`, and the full updated `question` object.
2. `app/schemas/__init__.py`: Exported `QuestionReviewRequest` and `QuestionReviewResponse`.
3. `app/services/question_service.py`: Implemented `QuestionService.review_question`:
   - Validates question existence (404 if not found).
   - Validates lifecycle status: strictly rejects questions whose status is not `PENDING_REVIEW` (400 Bad Request).
   - Deterministic status mapping: `APPROVE` $\rightarrow$ `QuestionStatus.APPROVED`, `REJECT` $\rightarrow$ `QuestionStatus.REJECTED`.
   - Single-transaction atomic persistence: inserts `QuestionReview` and updates `question.status` together; executes `db.rollback()` on error.
4. `app/routers/questions.py`: Added endpoint:
   - `POST /api/v1/questions/{question_id}/review`
   - Protected with `require_roles(RoleName.SME, RoleName.ADMIN)`.
5. `tests/test_questions.py`: Added 11 automated test cases verifying authentication, role access control, state transitions, atomic rollbacks, and database audit persistence.
6. `backend/README.md`: Updated with Phase 6 architecture, endpoint documentation, and verification status.

### Created Files:
1. `scratch/verify_phase_6_review.py`: Live end-to-end verification script testing live PostgreSQL, ChromaDB, and RBAC rules.
2. `PHASE_6_REPORT.md` (root and `backend/`).

---

## 3. Core Architectural Highlights & Compliance with Directives

### 1. Zero Database Schema Alterations
- Phase 2 established a forward-compatible 16-table PostgreSQL schema.
- The `question_reviews` table already contained all required fields: `id`, `question_id`, `reviewer_id`, `action`, `comment`, and `created_at`.
- PostgreSQL enums `question_status_enum` (`['PENDING_REVIEW', 'APPROVED', 'REJECTED']`) and `review_action_enum` (`['APPROVE', 'REJECT']`) were already defined and in place.
- **Zero migrations and zero DDL changes** were performed.

### 2. Strict Role-Based Access Control (RBAC)
- Reviewing questions is strictly restricted to `SME` and `ADMIN` roles:
  - `require_roles(RoleName.SME, RoleName.ADMIN)` is enforced as a FastAPI route dependency.
  - `TRAINER` and `OFFICER` attempts return `HTTP 403 Forbidden`.
  - Unauthenticated requests return `HTTP 401 Unauthorized`.

### 3. Strict State Transition Lifecycle
- Only questions with `status == QuestionStatus.PENDING_REVIEW` can be evaluated.
- If an SME attempts to review an already `APPROVED` or `REJECTED` question, the backend returns `HTTP 400 Bad Request` with an explanatory message:
  ```json
  {"detail": "Question 187 has status 'APPROVED' and cannot be reviewed again."}
  ```
- This prevents race conditions, conflicting SME decisions, and double-review corruption.

### 4. Single-Transaction Atomic Audit Persistence
- The creation of the `QuestionReview` record and the mutation of `question.status` are executed within the same database transaction.
- If an exception occurs during review creation or state update, `db.rollback()` is invoked, ensuring the database is never left with an updated question status lacking an audit record, or vice versa.

### 5. Provenance & Traceability Preserved
- All source attribution established in Phase 5 (`source_chunk_id`, `source_page`, `generation_model`, `competency_id`) remains completely intact and immutable during SME review.
- The reviewer's identity (`reviewer_id`), review decision (`APPROVE`/`REJECT`), timestamp (`created_at`), and justification (`comment`) are permanently linked to the question.

### 6. No Redundant Endpoints
- The existing `GET /api/v1/questions?status=PENDING_REVIEW` endpoint naturally serves as the SME review queue. No duplicate `/review-queue` endpoint was created, maintaining API cleanliness.

---

## 4. API Endpoints Reference

| Method | Endpoint | Authorized Roles | Description | Status Code |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/questions/{id}/review` | `SME`, `ADMIN` | Submit SME review decision (`APPROVE` or `REJECT`) with optional comment | `200 OK` |
| `GET` | `/api/v1/questions` | `TRAINER`, `SME`, `ADMIN` | List questions filtered by `status` (e.g. `PENDING_REVIEW`), `document_id`, `competency_id` | `200 OK` |
| `GET` | `/api/v1/questions/{id}` | `TRAINER`, `SME`, `ADMIN` | View complete question details, distractors, explanation, and source citations | `200 OK` |
| `POST` | `/api/v1/questions/generate` | `TRAINER`, `ADMIN` | Generate RAG-based MCQs from processed MoSPI documents | `201 Created` |

### Sample Review Request:
```http
POST /api/v1/questions/187/review
Authorization: Bearer <SME_OR_ADMIN_JWT_TOKEN>
Content-Type: application/json

{
  "action": "APPROVE",
  "comment": "Accurate calculation logic and faithful citation of ASI guidelines."
}
```

### Sample Review Response:
```json
{
  "id": 14,
  "question_id": 187,
  "reviewer_id": 967,
  "action": "APPROVE",
  "comment": "Accurate calculation logic and faithful citation of ASI guidelines.",
  "created_at": "2026-09-26T22:44:15.123456+05:30",
  "question_status": "APPROVED",
  "question": {
    "id": 187,
    "document_id": 42,
    "competency_id": 18,
    "question_text": "Under MoSPI ASI survey methodology, how is capital depreciation handled?",
    "option_a": "Depreciation is evaluated based on historical cost book values.",
    "option_b": "Depreciation is excluded from Gross Value Added calculations.",
    "option_c": "Depreciation is replaced with full capital replacement expenditure.",
    "option_d": "Depreciation is calculated as a fixed five percent flat rate.",
    "correct_option": "A",
    "difficulty": "MEDIUM",
    "explanation": "According to ASI manual chunk 102 (page 2), depreciation is recorded as per accounting books of the registered factory.",
    "source_page": 2,
    "source_chunk_id": 102,
    "generation_model": "mistral-large-latest",
    "status": "APPROVED",
    "created_by": 966,
    "created_at": "2026-09-26T22:44:14.000000+05:30",
    "updated_at": "2026-09-26T22:44:15.000000+05:30"
  }
}
```

---

## 5. Verification Results

### A. Automated Test Suite (Pytest)
Command:
```powershell
python -m pytest -v
```

Output:
```text
============================= test session starts =============================
platform win32 -- Python 3.14.5, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\SIH\backend
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.13.0, langsmith-0.8.5
collected 97 items

tests\test_auth.py .............................                         [ 29%]
tests\test_documents.py ........................                         [ 54%]
tests\test_health.py .....                                               [ 59%]
tests\test_models.py ..........                                          [ 70%]
tests\test_questions.py .............................                    [100%]

======================= 97 passed, 2 warnings in 6.81s ========================
```

**Results**: All **97 automated tests passed** (86 baseline + 11 new Phase 6 review tests) with 0 failures and 0 API credit usage.

### B. Live PostgreSQL & ChromaDB Verification
Script: `scratch/verify_phase_6_review.py`
Verified checks against live PostgreSQL:
1. `[OK]` Test users & RBAC credentials created (Trainer, SME, Officer, Admin).
2. `[OK]` Multi-page PDF ingested and 3 MCQs generated in `PENDING_REVIEW` state.
3. `[OK]` SME queried review queue via `GET /api/v1/questions?status=PENDING_REVIEW`.
4. `[OK]` SME approved Question #1 $\rightarrow$ `status = APPROVED`, `action = APPROVE`.
5. `[OK]` SME rejected Question #2 $\rightarrow$ `status = REJECTED`, `action = REJECT` with SME critique.
6. `[OK]` Database verification confirmed: `question_reviews` records persisted, source chunk provenance preserved.
7. `[OK]` State transition rule verified: Repeated review on `APPROVED` and `REJECTED` questions returns `HTTP 400 Bad Request`.
8. `[OK]` RBAC verified: `OFFICER` and `TRAINER` roles forbidden from reviewing questions (`HTTP 403 Forbidden`).
9. `[OK]` Admin role review verified: System Administrator can also approve questions.
10. `[OK]` Nonexistent question ID returns `HTTP 404 Not Found`.

---

## 6. Conclusion & Readiness for Phase 7

Phase 6 is 100% complete and verified. The human-in-the-loop quality gate ensures only verified, high-quality MCQs enter the question bank.

The backend is now prepared for **Phase 7: Officer Competency Assessment & Diagnostic Testing**:
- Serving `APPROVED` questions to officers for skill assessments.
- Recording assessment attempts and question-level responses.
- Computing assessment scores and skill gap percentages.
- Linking diagnostic outcomes to MoSPI competency domains and iGOT courses.
