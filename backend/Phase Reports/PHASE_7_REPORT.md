# StatKarmayogi — Phase 7 Implementation Report
## Officer Assessment, Deterministic Scoring & Competency Gap Analysis

**Smart India Hackathon 2026**  
- **Problem Statement ID**: SIH26101  
- **Organization**: Ministry of Statistics and Programme Implementation (MoSPI)  
- **Theme**: Smart Education  
- **Phase**: Phase 7 — Officer Assessment, Deterministic Scoring & Competency Gap Analysis  
- **Status**: Completed & Fully Verified  

---

## 1. Objective

Phase 7 implements the core competency assessment engine for StatKarmayogi. It transitions the platform from content ingestion and SME question validation into the diagnostic testing workflow:

$$\text{Approved MCQs} \longrightarrow \text{Assessment Creation} \longrightarrow \text{Answer Submission} \longrightarrow \text{Deterministic Scoring} \longrightarrow \text{Competency Results} \longrightarrow \text{Skill Gaps}$$

Key accomplishments:
- Allows MoSPI Statistical Officers to take diagnostic assessments dynamically assembled from SME-approved MCQs (`QuestionStatus.APPROVED`).
- Enforces strict exam security by masking answer keys, explanations, and citations while an assessment is `IN_PROGRESS`.
- Implements deterministic, zero-AI, server-side scoring for overall performance and competency-level evaluation.
- Evaluates competency proficiency levels (`BEGINNER`, `DEVELOPING`, `PROFICIENT`, `ADVANCED`) and detects skill gaps (`HIGH`, `MEDIUM`, `LOW`) persisted in PostgreSQL.
- Executes answer evaluation, score calculation, competency result generation, and skill-gap persistence in a single atomic database transaction.
- Strictly respects the Phase 8 boundary (no course recommendations, no iGOT API integration, no learning pathways).

---

## 2. Existing Schema Reused & Confirmation of ZERO Schema Changes

In accordance with the pre-implementation inspection directive:
- Reused existing PostgreSQL tables: `assessments`, `assessment_questions`, `answers`, `competency_results`, `skill_gaps`, `questions`, `competencies`, `users`, `documents`.
- Reused existing PostgreSQL enums:
  - `assessment_status_enum`: `['IN_PROGRESS', 'COMPLETED']`
  - `proficiency_level_enum`: `['BEGINNER', 'DEVELOPING', 'PROFICIENT', 'ADVANCED']`
  - `gap_level_enum`: `['HIGH', 'MEDIUM', 'LOW']`
- **Zero database migrations, zero DDL alterations, and zero schema changes** were created or needed. Exactly 16 tables remain in PostgreSQL.

---

## 3. Files Created / Modified

### Files Created:
1. `app/schemas/assessment.py`: Pydantic v2 schemas:
   - `AssessmentCreateRequest`: Payload for creating an assessment (`title`, `question_count`, `competency_id`, `document_id`, `officer_id`).
   - `AssessmentQuestionResponse`: Safe, officer-facing question representation with zero answer key leakage.
   - `AnswerSubmission`: Individual question answer payload (`question_id`, `selected_option`).
   - `AssessmentSubmitRequest`: Batch submission payload (`answers`).
   - `CompetencyResultResponse`: Per-competency score and proficiency level.
   - `SkillGapResponse`: Identified competency deficiency and gap level.
   - `AssessmentQuestionDetailResponse`: Unmasked question review with explanations and source citations (only after completion).
   - `AssessmentResponse`: Metadata and active state representation.
   - `AssessmentDetailResponse`: Detailed view with questions.
   - `AssessmentListResponse`: Paginated collection of assessments.
   - `AssessmentResultResponse`: Aggregated evaluated outcome report.
2. `app/services/assessment_service.py`: Business service orchestrating:
   - Deterministic question selection (`ORDER BY questions.id ASC`).
   - Configurable prototype proficiency and gap calculations.
   - Single-transaction atomic submission and rollback safety.
   - RBAC ownership enforcement.
3. `app/routers/assessments.py`: FastAPI route handlers for the 5 core assessment endpoints.
4. `tests/test_assessments.py`: 28 comprehensive pytest test cases verifying RBAC, deterministic selection, answer masking, submission validation, deterministic scoring, competency results, skill gaps, atomic rollback, and error handling.
5. `scratch/verify_phase_7_assessment.py`: Live end-to-end verification script testing all 18 lifecycle steps against the development PostgreSQL database.

### Files Modified:
1. `app/core/config.py`: Added configurable prototype thresholds and assessment volume settings:
   - `DEFAULT_ASSESSMENT_QUESTION_COUNT: int = 10`
   - `MAX_ASSESSMENT_QUESTION_COUNT: int = 50`
   - `ADVANCED_THRESHOLD: float = 80.0`
   - `PROFICIENT_THRESHOLD: float = 65.0`
   - `DEVELOPING_THRESHOLD: float = 50.0`
2. `app/schemas/__init__.py`: Exported all assessment schemas.
3. `app/services/__init__.py`: Exported `AssessmentService`.
4. `app/routers/__init__.py`: Exported `assessments_router`.
5. `app/main.py`: Included `assessments_router` under prefix `/api/v1`.
6. `backend/README.md`: Documented Phase 7 architecture, endpoints, and updated test suite count (125 tests).

---

## 4. API Endpoints

| Method | Endpoint | Authorized Roles | Description | Status Code |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/assessments` | `OFFICER`, `ADMIN` | Create assessment from approved competency-tagged MCQs | `201 Created` |
| `GET` | `/api/v1/assessments` | `OFFICER` (own), `TRAINER`, `ADMIN` (all) | List assessments with ownership filtering and pagination | `200 OK` |
| `GET` | `/api/v1/assessments/{id}` | `OFFICER` (owner), `TRAINER`, `ADMIN` | Get assessment details (masked questions if `IN_PROGRESS`) | `200 OK` |
| `POST` | `/api/v1/assessments/{id}/submit` | `OFFICER` (owner), `ADMIN` | Atomically submit all answers, evaluate correctness, and score | `200 OK` |
| `GET` | `/api/v1/assessments/{id}/result` | `OFFICER` (owner), `TRAINER`, `ADMIN` | Retrieve evaluated results, competency scores, and skill gaps | `200 OK` |

> [!NOTE]
> No `/attempts` or `/attempts/{id}` public endpoints were introduced. All operations function directly on `/api/v1/assessments` per the relational architecture where `assessments.officer_id` represents the assessment instance.

---

## 5. RBAC Authorization Matrix

| Operation | OFFICER | TRAINER | SME | ADMIN |
| :--- | :---: | :---: | :---: | :---: |
| Create own assessment | ✅ | ❌ (403) | ❌ (403) | ✅ |
| Create assessment for an officer | ❌ (403) | ❌ (403) | ❌ (403) | ✅ |
| List own assessments | ✅ | ✅ (all) | ❌ (403) | ✅ (all) |
| View assessment (masked during exam) | ✅ (own only) | ✅ | ❌ (403) | ✅ |
| Submit assessment answers | ✅ (own only) | ❌ (403) | ❌ (403) | ✅ (own only) |
| View completed results & skill gaps | ✅ (own only) | ✅ | ❌ (403) | ✅ |

---

## 6. Assessment Lifecycle

The lifecycle uses the existing PostgreSQL `assessment_status_enum`:

$$\textbf{IN\_PROGRESS} \xrightarrow{\quad\text{Atomic Submission}\quad} \textbf{COMPLETED}$$

- **IN_PROGRESS**:
  - Assigned questions are served with answer keys strictly hidden (`correct_option`, `is_correct`, `explanation`, `source_page`, `source_chunk_id` omitted).
  - Calling `GET /api/v1/assessments/{id}/result` is blocked (`HTTP 400 Bad Request`).
- **COMPLETED**:
  - All assigned questions are evaluated, scores and competency metrics are recorded, and status transitions to `COMPLETED`.
  - Calling `GET /api/v1/assessments/{id}/result` exposes the full diagnostic report.
  - Calling `POST /api/v1/assessments/{id}/submit` again is blocked (`HTTP 400 Bad Request`).

---

## 7. Deterministic Question Selection

Question assignment follows strict deterministic rules:
1. `Question.status == QuestionStatus.APPROVED` (strictly excludes `PENDING_REVIEW` and `REJECTED`).
2. `Question.competency_id IS NOT NULL` (diagnostic testing requires competency tagging; questions without competency are excluded).
3. Optional filters applied: `Question.competency_id == request.competency_id` and `Question.document_id == request.document_id`.
4. Deterministic ordering: `ORDER BY questions.id ASC`.
5. Limit to `request.question_count`.
6. If available matching questions $< \text{request.question_count}$, raises `HTTP 400 Bad Request` ("Insufficient approved competency-tagged questions available for this assessment.").

---

## 8. Deterministic Scoring Algorithm

All scoring is performed server-side with zero AI, zero embeddings, and deterministic logic:

1. **Answer Correctness**:
   $$\text{is\_correct} = (\text{submitted\_option.upper}() == \text{question.correct\_option.upper}())$$
2. **Overall Score**:
   $$\text{score\_percentage} = \operatorname{round}\left(\frac{\text{total\_correct}}{\text{total\_questions}} \times 100, 2\right)$$

---

## 9. Configurable Prototype Proficiency Thresholds

> [!IMPORTANT]
> **Explicit Note**: These are configurable prototype scoring thresholds configured in `app/core/config.py` and are **not presented as official MoSPI competency thresholds**.

Configured defaults:
```python
ADVANCED_THRESHOLD = 80.0
PROFICIENT_THRESHOLD = 65.0
DEVELOPING_THRESHOLD = 50.0
```

Deterministic mapping function:
```python
if score_percentage >= settings.ADVANCED_THRESHOLD:
    return ProficiencyLevel.ADVANCED
elif score_percentage >= settings.PROFICIENT_THRESHOLD:
    return ProficiencyLevel.PROFICIENT
elif score_percentage >= settings.DEVELOPING_THRESHOLD:
    return ProficiencyLevel.DEVELOPING
else:
    return ProficiencyLevel.BEGINNER
```

---

## 10. Competency-Level Evaluation

Answered questions are grouped by `question.competency_id`. For each competency:
- `questions_attempted` = count of assigned questions for this competency.
- `questions_correct` = count of correct answers for this competency.
- `score_percentage` = $\operatorname{round}\left(\frac{\text{questions\_correct}}{\text{questions\_attempted}} \times 100, 2\right)$.
- `proficiency_level` = mapped via prototype thresholds.
- Result is persisted into the existing `competency_results` table respecting `uq_assessment_competency_result` (`assessment_id`, `competency_id`).

---

## 11. Skill Gap Identification

Identifies competency deficiencies to prepare data for Phase 8 recommendations:
- Score $< \text{DEVELOPING\_THRESHOLD}$ ($< 50\%$) $\implies \textbf{GapLevel.HIGH}$ (Severe deficiency)
- $\text{DEVELOPING\_THRESHOLD} \le \text{Score} < \text{PROFICIENT\_THRESHOLD}$ ($50\% - 64.99\%$) $\implies \textbf{GapLevel.MEDIUM}$ (Moderate deficiency)
- $\text{PROFICIENT\_THRESHOLD} \le \text{Score} < \text{ADVANCED\_THRESHOLD}$ ($65\% - 79.99\%$) $\implies \textbf{GapLevel.LOW}$ (Minor deficiency)
- $\text{Score} \ge \text{ADVANCED\_THRESHOLD}$ ($\ge 80\%$) $\implies \textbf{No Skill Gap}$ (Mastery achieved)
- Persisted into the existing `skill_gaps` table respecting `uq_assessment_competency_gap` (`assessment_id`, `competency_id`).

---

## 12. Security & Answer Key Masking

To ensure exam integrity:
- Active assessment endpoint (`GET /api/v1/assessments/{id}`) uses `AssessmentQuestionResponse` which completely omits:
  - `correct_option`
  - `is_correct`
  - `explanation`
  - `source_page`
  - `source_chunk_id`
  - `generation_model`
- Full evaluation and educational explanations are unmasked **only** via `GET /api/v1/assessments/{id}/result` after the assessment status is `COMPLETED`.

---

## 13. Transaction Atomicity & Rollback

Assessment submission executes in a single database transaction:
1. Validates ownership, active status, unassigned questions, and complete question answering (partial/empty submissions rejected).
2. Persists all answers in `answers`.
3. Updates `assessments` (`total_questions`, `total_correct`, `score_percentage`, `status=COMPLETED`, `completed_at=now()`).
4. Persists all records in `competency_results`.
5. Persists all detected gaps in `skill_gaps`.
6. Executes `db.commit()`. If any error occurs, executes `db.rollback()` leaving zero orphaned records.
7. Explicitly tested via `test_submit_atomic_rollback` verifying that a simulated exception during submission triggers rollback and leaves the assessment `IN_PROGRESS` with zero partial records.

---

## 14. Automated Verification Results (Pytest)

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
collected 125 items

tests\test_assessments.py ............................                   [ 22%]
tests\test_auth.py .............................                         [ 45%]
tests\test_documents.py ........................                         [ 64%]
tests\test_health.py .....                                               [ 68%]
tests\test_models.py ..........                                          [ 76%]
tests\test_questions.py .............................                    [100%]

======================= 125 passed, 2 warnings in 7.04s =======================
```

**Results**: All **125 automated tests passed** (97 previous regression tests + 28 Phase 7 tests) with 0 failures and 0 API credit usage.

---

## 15. Live Manual Verification Results

Script: `scratch/verify_phase_7_assessment.py` executed against live PostgreSQL (`localhost:5432/statkarmayogi_db`):
- `[OK]` Step 1: Seeded roles and authenticated test personas (Officer 1, Officer 2, Trainer, SME, Admin).
- `[OK]` Step 2: Created competencies: 'ASI Survey Methodology' and 'Index of Industrial Production (IIP)'.
- `[OK]` Step 3: Created 4 APPROVED questions + 1 pending, 1 rejected, and 1 null-competency question.
- `[OK]` Step 4: Officer 1 created assessment (ID=212, status=IN_PROGRESS).
- `[OK]` Step 5: Deterministic question ordering verified (questions ordered by ID ASC).
- `[OK]` Step 6: Security verified — answer keys, explanations, and citations strictly masked.
- `[OK]` Step 7: Results endpoint blocked while IN_PROGRESS (400).
- `[OK]` Step 8: RBAC verified — Trainer and SME creation attempts rejected (403).
- `[OK]` Step 9: Empty submission correctly rejected (400).
- `[OK]` Step 10: Partial submission correctly rejected (400) — all questions must be answered.
- `[OK]` Step 11: Duplicate question submission correctly rejected (400).
- `[OK]` Step 12: Unassigned question submission correctly rejected (400).
- `[OK]` Step 13: Overall score calculated deterministically: 3/4 correct = 75.0%, status=COMPLETED.
- `[OK]` Step 14: Competency ASI scored 100% -> Proficiency: ADVANCED.
- `[OK]` Step 15: Competency IIP scored 50% -> Proficiency: DEVELOPING.
- `[OK]` Step 16: Skill gap verified: Competency IIP identified as GapLevel.MEDIUM (50%).
- `[OK]` Step 17: Detailed question review unmasked with explanations and citations.
- `[OK]` Step 18: Repeated submission of completed assessment correctly rejected (400).
- `[OK]` Step 19: Officer data isolation enforced (Officer 2 receives 403 on Officer 1's assessment).
- `[OK]` Step 20: Trainer and Admin can inspect completed assessment results.
- `[OK]` Step 21: Database records directly verified in PostgreSQL (`answers`, `competency_results`, `skill_gaps`).
- `[OK]` Step 22: ZERO schema changes confirmed — exactly 16 existing tables present.

---

## 16. Explicit Phase Boundary

- **Phase 7 Implementation Ends Here**:
  - Assessment creation, question assignment, answer submission, deterministic scoring, competency evaluation, and skill gap identification are 100% complete and verified.
- **Phase 8 (iGOT Course Recommendations & Adaptive Learning Pathways)**:
  - Phase 8 will match the `skill_gaps` persisted in Phase 7 against the `courses` and `course_competencies` catalogue to generate explainable course recommendations.
  - Zero Phase 8 functionality has been implemented.
