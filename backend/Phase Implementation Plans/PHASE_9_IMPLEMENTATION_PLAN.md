# Implementation Plan: Phase 9 — Reassessment & Closed Learning Loop

**StatKarmayogi — AI-Driven Competency Assessment & Adaptive iGOT Learning Pathway for MoSPI (SIH26101)**

---

## 1. Goal & Functional Milestone Overview

Implement **Phase 9: Reassessment & Closed Learning Loop** for the StatKarmayogi backend.

Phase 9 completes the overarching MoSPI capability-building feedback loop by connecting diagnostic assessment, skill gap identification, iGOT learning recommendations, course completion, and post-learning reassessment:

```text
┌─────────────────────────────────┐
│     1. Baseline Assessment      │  (Diagnostic MCQs based on approved MoSPI documents)
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│    2. Identify Skill Gaps       │  (HIGH, MEDIUM, LOW deficiency levels)
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│   3. iGOT Recommendations       │  (Deterministic course recommendations with match scores)
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│  4. Officer Completes Learning  │  (Status transitioned: RECOMMENDED → STARTED → COMPLETED)
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│   5. Targeted Reassessment      │  (Scoped evaluation on gap competencies)
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│   6. Compare Before vs After    │  (Granular score deltas & proficiency level transitions)
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│   7. Closed Learning Loop       │  (Measure gap resolution & correlate learning activity)
└─────────────────────────────────┘
```

### Core Objectives:
1. **Targeted Reassessment Creation**: Allow an officer (or Admin) to initiate a focused reassessment linked to a completed baseline assessment, targeting the competencies where skill gaps were identified.
2. **Preserve Baseline Integrity**: Keep the original baseline assessment instance, questions, answers, competency results, skill gaps, and recommendations 100% immutable and intact.
3. **Record Separate Reassessment Instances**: Represent each reassessment attempt as an independent `Assessment` record with its own deterministic scoring, answers, and results.
4. **Deterministic Before/After Comparison**: Reuse the exact Phase 7 scoring scale and thresholds to compute granular score deltas, proficiency progression, and gap resolution states.
5. **Learning Context Correlation**: Correlate completed iGOT learning activities (`status = COMPLETED`) with competency improvements without making unscientific causal claims.
6. **Support Multiple Attempts**: Enable longitudinal tracking across multiple reassessment attempts (Attempt 1, Attempt 2, etc.) while preserving full historical progression.
7. **Zero Schema Modifications**: Accomplish the entire milestone using the **existing 16 PostgreSQL tables** with **zero migrations, zero DDL statements, zero new columns, and zero enum changes**.

---

## 2. Current-State Codebase & Schema Inspection

A thorough inspection of the live PostgreSQL database (`localhost:5432/statkarmayogi_db`) and backend codebase revealed the following capabilities and constraints:

### 2.1 Schema Inspection (Exactly 16 Tables)

| Table Name | Existing Columns & Primary Keys | Reassessment Role |
| :--- | :--- | :--- |
| `assessments` | `id`, `officer_id`, `title`, `status`, `total_questions`, `total_correct`, `score_percentage`, `started_at`, `completed_at` | Stores both baseline assessments and subsequent reassessment instances. `officer_id` is a 1-to-many relationship allowing multiple attempts. |
| `assessment_questions` | `id`, `assessment_id`, `question_id`, `question_order` | Links each reassessment instance to its assigned approved MCQs. |
| `answers` | `id`, `assessment_id`, `question_id`, `selected_option`, `is_correct`, `answered_at` | Records submitted officer answers for the reassessment instance. |
| `competency_results` | `id`, `assessment_id`, `competency_id`, `questions_attempted`, `questions_correct`, `score_percentage`, `proficiency_level`, `created_at` | Stores evaluated proficiency per competency for the reassessment. Used directly for $\Delta$ calculation. |
| `skill_gaps` | `id`, `assessment_id`, `competency_id`, `score_percentage`, `gap_level`, `created_at` | Stores post-reassessment skill gaps. Compared against baseline gaps to determine resolution status. |
| `recommendations` | `id`, `officer_id`, `assessment_id`, `competency_id`, `course_id`, `priority`, `match_score`, `reason`, `status`, `created_at` | Source of preceding learning activity (`status == COMPLETED`). Also receives new recommendations if gaps persist. |
| `courses` | `id`, `igot_course_id`, `title`, `description`, `provider`, `language`, `difficulty`, `duration_minutes`, `course_url`, `is_public`, `is_active`, `source` | Catalogue metadata for courses completed prior to reassessment. |
| `course_competencies` | `id`, `course_id`, `competency_id`, `relevance_score`, `created_at` | Links completed courses back to specific evaluated competencies. |
| `competencies` | `id`, `code`, `name`, `description`, `category`, `is_active` | Competency taxonomy used across both baseline and reassessment. |
| `users` | `id`, `name`, `email`, `password_hash`, `role_id`, `department`, `designation`, `is_active` | Officer ownership and RBAC enforcement. |
| `roles` | `id`, `name` | RBAC roles (`OFFICER`, `TRAINER`, `ADMIN`, `SME`). |
| `questions` | `id`, `document_id`, `competency_id`, `question_text`, `option_a`, `option_b`, `option_c`, `option_d`, `correct_option`, `difficulty`, `explanation`, `source_page`, `source_chunk_id`, `generation_model`, `status`, `created_by` | Source of approved MCQs (`status = APPROVED`) assigned to reassessment. |
| `question_reviews` | `id`, `question_id`, `reviewer_id`, `action`, `comment`, `created_at` | SME audit trail for approved questions. |
| `documents` | `id`, `uploaded_by`, `filename`, `file_type`, `file_path`, `status`, `processing_error`, `generation_count` | MoSPI source publications. |
| `document_chunks` | `id`, `document_id`, `chunk_index`, `page_number`, `content_hash`, `chroma_id` | Chunks underpinning question generation. |
| `alembic_version` | `version_num` | Migration state (remains at initial version `02255fcc9e4b`). |

### 2.2 Inspection Findings on Schema Sufficiency

> [!IMPORTANT]
> **ZERO SCHEMA CHANGES REQUIRED**:
> The existing 16-table PostgreSQL schema **already possesses complete relational support** for the closed learning loop:
> 1. An officer can have an arbitrary number of `Assessment` records (`officer_id` is a standard non-unique foreign key).
> 2. Each `Assessment` instance independently owns its `assessment_questions`, `answers`, `competency_results`, and `skill_gaps`.
> 3. Baseline assessments and reassessments use identical competency measurement semantics (`score_percentage`, `proficiency_level`, `gap_level`), making mathematical comparison direct and unambiguous.
> 4. Preceding learning history is explicitly tracked in `recommendations.status` (`COMPLETED`, `STARTED`).
> 5. Linking a reassessment to its baseline assessment is cleanly handled via the existing `title` field convention (e.g. `Reassessment [Baseline #{baseline_id}]: {title}`) and API parameters, requiring **zero DDL modifications, zero new tables, and zero new columns**.

---

## 3. Assessment vs. Reassessment Relationship & Modeling

### 3.1 Separate Attempt Paradigm

The system adopts a **discrete assessment instance paradigm**:
- **Baseline Assessment**: The initial diagnostic assessment taken by the officer (e.g. `Assessment #10`). Its records are immutable once `status = COMPLETED`.
- **Reassessment Attempt**: A newly instantiated `Assessment` record (e.g. `Assessment #15`), created specifically after learning activity has occurred.
- **Linkage Mechanism**:
  1. **Primary Link**: Stored in the `title` attribute using a deterministic prefix:
     ```text
     "Reassessment [Baseline #10]: ASI Survey Diagnostic"
     ```
  2. **API Endpoint Route**: Initiated via `POST /api/v1/assessments/{baseline_id}/reassess`, which establishes the link explicitly in the business logic.
  3. **Comparison Resolution**: The comparison endpoint `GET /api/v1/assessments/{reassessment_id}/comparison` parses `baseline_id` from the title or accepts an explicit `?baseline_id={id}` query parameter.

### 3.2 Immutability Guarantees

```text
┌────────────────────────────────────────────────────────────────────────┐
│                   IMMUTABILITY CONTRACT                                │
├────────────────────────────────────────────────────────────────────────┤
│ When a Reassessment is created or submitted:                           │
│ - Baseline `assessments` row: UNCHANGED                                │
│ - Baseline `assessment_questions`: UNCHANGED                           │
│ - Baseline `answers`: UNCHANGED                                        │
│ - Baseline `competency_results`: UNCHANGED                             │
│ - Baseline `skill_gaps`: UNCHANGED                                     │
│ - Baseline `recommendations`: UNCHANGED                                │
│                                                                        │
│ All reassessment scoring and gaps are written to NEW rows              │
│ associated with the NEW `reassessment.id`.                             │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Deterministic Before / After Comparison Algorithm

### 4.1 Measurement Semantics (Phase 7 Reused)

The before/after comparison strictly reuses the established Phase 7 thresholds from [`app/core/config.py`](file:///c:/SIH/backend/app/core/config.py):
- `ADVANCED_THRESHOLD = 80.0`
- `PROFICIENT_THRESHOLD = 65.0`
- `DEVELOPING_THRESHOLD = 50.0`

Proficiency Levels:
- **`ADVANCED`**: $\text{score} \ge 80.0\%$
- **`PROFICIENT`**: $65.0\% \le \text{score} < 80.0\%$
- **`DEVELOPING`**: $50.0\% \le \text{score} < 65.0\%$
- **`BEGINNER`**: $\text{score} < 50.0\%$

Skill Gap Levels:
- **`HIGH`**: $\text{score} < 50.0\%$
- **`MEDIUM`**: $50.0\% \le \text{score} < 65.0\%$
- **`LOW`**: $65.0\% \le \text{score} < 80.0\%$
- **`None` / `RESOLVED`**: $\text{score} \ge 80.0\%$ (Target benchmark achieved)

### 4.2 Mathematical Formulas

For each competency $c$ evaluated in both the baseline ($B$) and reassessment ($R$):

1. **Score Delta**:
   $$\Delta_{\text{score}}(c) = \operatorname{round}(S_R(c) - S_B(c), 2)$$
   Where $S_R(c)$ is the reassessment percentage and $S_B(c)$ is the baseline percentage.

2. **Competency Improvement Direction**:
   $$\text{status}(c) = \begin{cases}
   \text{IMPROVED} & \text{if } \Delta_{\text{score}}(c) > 0.0 \\
   \text{UNCHANGED} & \text{if } \Delta_{\text{score}}(c) = 0.0 \\
   \text{DECLINED} & \text{if } \Delta_{\text{score}}(c) < 0.0
   \end{cases}$$

3. **Overall Assessment Delta**:
   $$\Delta_{\text{overall}} = \operatorname{round}(S_{R,\text{overall}} - S_{B,\text{overall}}, 2)$$

### 4.3 Skill Gap Resolution State Machine

Comparing the baseline gap level $G_B(c)$ to the reassessment gap level $G_R(c)$:

| Baseline Gap $G_B(c)$ | Reassessment Gap $G_R(c)$ | Resolution State | Description |
| :---: | :---: | :---: | :--- |
| `HIGH`, `MEDIUM`, or `LOW` | `None` ($\ge 80\%$) | **`RESOLVED`** | Competency gap completely eliminated. Benchmark achieved. |
| `HIGH` | `MEDIUM` or `LOW` | **`REDUCED`** | Significant improvement, severity reduced. |
| `MEDIUM` | `LOW` | **`REDUCED`** | Improvement observed, severity reduced. |
| `HIGH` | `HIGH` | **`PERSISTENT`** | No change in severity tier. Ongoing deficiency. |
| `MEDIUM` | `MEDIUM` | **`PERSISTENT`** | No change in severity tier. Ongoing deficiency. |
| `LOW` | `LOW` | **`PERSISTENT`** | No change in severity tier. Ongoing deficiency. |
| `MEDIUM` or `LOW` | `HIGH` | **`INCREASED`** | Competency worsened. Severity increased. |
| `LOW` | `MEDIUM` | **`INCREASED`** | Competency worsened. Severity increased. |
| `None` ($\ge 80\%$) | `None` ($\ge 80\%$) | **`NO_GAP`** | Mastery sustained across both assessments. |
| `None` ($\ge 80\%$) | `HIGH`, `MEDIUM`, `LOW` | **`NEW_GAP`** | Previously mastered competency dropped below benchmark. |

### 4.4 Closed Loop Status Evaluation

The overall learning loop outcome is classified into one of three macro-states:
1. **`LOOP_CLOSED`**: Every skill gap identified in the baseline assessment is now `RESOLVED` ($G_R(c) = \text{None}, \forall c \in \text{Gaps}_B$).
2. **`PARTIALLY_CLOSED`**: At least one baseline gap is `RESOLVED` or `REDUCED`, but one or more gaps remain active.
3. **`LOOP_OPEN`**: Zero baseline gaps improved, or competencies declined. Further learning intervention required.

---

## 5. Learning-Link & Correlation Context

### 5.1 Correlation Protocol (Non-Causal Representation)

The comparison engine identifies learning activities completed between the baseline and reassessment:
1. Queries `recommendations` associated with `assessment_id = baseline_id` where `status == RecommendationStatus.COMPLETED` (or `STARTED`).
2. Matches each completed course to its covered competencies via `CourseCompetency`.
3. Displays the completed course alongside the competency delta.

> [!NOTE]
> **NON-CAUSAL SCIENTIFIC ATTRIBUTION**:
> In accordance with official MoSPI evaluation principles, the report clearly provides learning context as an **educational correlation**, explicitly noting:
> *"Officer completed course '[Course Title]' prior to reassessment. Competency score changed from X% to Y% (+Z%). This learning activity is documented as developmental context and educational correlation, not formal causal proof."*

---

## 6. API Design & Endpoints

All endpoints will be mounted under prefix `/api/v1/assessments` reusing the project's standard FastAPI conventions.

### Endpoint 1: Create Targeted Reassessment
- **Method**: `POST`
- **Path**: `/api/v1/assessments/{baseline_id}/reassess`
- **Description**: Initiates a targeted reassessment linked to a completed baseline assessment.
- **Access**: `OFFICER` (owner of baseline) or `ADMIN`.
- **Request Body** (`ReassessmentCreateRequest`, optional):
  ```json
  {
    "title": "Optional custom reassessment title",
    "question_count": 10,
    "competency_ids": [57, 122]
  }
  ```
  *(If `competency_ids` is omitted, defaults automatically to all competencies where baseline had skill gaps).*
- **Validation**:
  - Baseline assessment must exist (`404`).
  - Baseline assessment must have `status == COMPLETED` (`400`).
  - Officer must own the baseline assessment unless Admin (`403`).
  - Baseline must have associated competencies (`400`).
- **Response**: `AssessmentDetailResponse` (`HTTP 201 Created`) with exam-safe masked questions (`correct_option` and explanations hidden).

### Endpoint 2: Submit Reassessment Answers
- **Method**: `POST`
- **Path**: `/api/v1/assessments/{reassessment_id}/submit`
- **Description**: Submits officer answers for the reassessment instance.
- **Access**: `OFFICER` (owner) or `ADMIN`.
- **Behavior**: Reuses the established Phase 7 `submit_assessment` workflow:
  - Validates full question completion.
  - Deterministically evaluates answers.
  - Commits `Answer`, `CompetencyResult`, and `SkillGap` records.
  - Transitions `reassessment.status = COMPLETED`.
  - Runs safe post-commit Phase 8 recommendation hook for any persistent gaps.
- **Response**: `AssessmentResultResponse` (`HTTP 200 OK`).

### Endpoint 3: Before vs. After Comparison
- **Method**: `GET`
- **Path**: `/api/v1/assessments/{reassessment_id}/comparison`
- **Query Parameter**: `baseline_id: Optional[int] = None`
- **Description**: Generates the comprehensive before/after comparison report for the closed learning loop.
- **Access**: `OFFICER` (owner), `TRAINER` (any officer), `ADMIN` (any officer). `SME` is rejected (`403`).
- **Behavior**:
  - If `baseline_id` is omitted, resolves `baseline_id` from the reassessment title header `Reassessment [Baseline #{id}]: ...` or queries the most recent completed baseline assessment for that officer.
  - Verifies both assessments are `COMPLETED`.
  - Calculates score deltas, proficiency tier changes, and gap resolution states.
  - Compiles associated completed courses.
- **Response**: `ReassessmentComparisonResponse` (`HTTP 200 OK`).

### Endpoint 4: List Reassessments for Baseline
- **Method**: `GET`
- **Path**: `/api/v1/assessments/{baseline_id}/reassessments`
- **Description**: Lists all reassessment attempts linked to a specific baseline assessment.
- **Access**: `OFFICER` (owner), `TRAINER`, `ADMIN`.
- **Response**: `ReassessmentListResponse` (`HTTP 200 OK`).

---

## 7. Pydantic Request & Response Schemas

Add the following schemas to `app/schemas/assessment.py`:

```python
class ReassessmentCreateRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=255, description="Custom title for reassessment")
    question_count: Optional[int] = Field(None, ge=1, le=50, description="Number of questions to assign")
    competency_ids: Optional[List[int]] = Field(None, description="Specific competency IDs to reassess")


class LearningContextItem(BaseModel):
    course_id: int
    igot_course_id: Optional[str]
    course_title: str
    status: str
    correlation_note: str


class CompetencyComparisonItem(BaseModel):
    competency_id: int
    competency_code: Optional[str]
    competency_name: str
    baseline_score: float
    baseline_proficiency: str
    baseline_gap_level: Optional[str]
    reassessment_score: float
    reassessment_proficiency: str
    reassessment_gap_level: Optional[str]
    delta: float
    improvement_status: str  # IMPROVED, UNCHANGED, DECLINED
    gap_resolution_status: str  # RESOLVED, REDUCED, PERSISTENT, INCREASED, NO_GAP, NEW_GAP
    associated_learning: List[LearningContextItem] = []


class ReassessmentComparisonResponse(BaseModel):
    baseline_assessment_id: int
    baseline_title: str
    baseline_completed_at: Optional[datetime]
    baseline_overall_score: float
    reassessment_assessment_id: int
    reassessment_title: str
    reassessment_completed_at: Optional[datetime]
    reassessment_overall_score: float
    overall_delta: float
    overall_improvement_status: str  # IMPROVED, UNCHANGED, DECLINED
    loop_status: str  # LOOP_CLOSED, PARTIALLY_CLOSED, LOOP_OPEN
    competency_comparisons: List[CompetencyComparisonItem]
    summary_narrative: str
```

---

## 8. Role-Based Access Control (RBAC) Specification

Phase 9 strictly adheres to the established project security model using `require_roles`:

| Action / Endpoint | `OFFICER` | `TRAINER` | `ADMIN` | `SME` |
| :--- | :---: | :---: | :---: | :---: |
| `POST /api/v1/assessments/{id}/reassess` | **Allowed** (Own baseline only) | **Forbidden** (403) | **Allowed** (Any officer) | **Forbidden** (403) |
| `POST /api/v1/assessments/{id}/submit` | **Allowed** (Own assessment only) | **Forbidden** (403) | **Forbidden** (Cannot submit for officer) | **Forbidden** (403) |
| `GET /api/v1/assessments/{id}/comparison` | **Allowed** (Own assessments only) | **Allowed** (All officers) | **Allowed** (All officers) | **Forbidden** (403) |
| `GET /api/v1/assessments/{id}/reassessments` | **Allowed** (Own baseline only) | **Allowed** (All officers) | **Allowed** (All officers) | **Forbidden** (403) |

---

## 9. Idempotency, History & Multi-Attempt Lifecycle

1. **Attempt Ordering & History**:
   - Each reassessment attempt is a unique row in `assessments`.
   - Ordering is strictly deterministic: `ORDER BY started_at ASC, id ASC`.
   - Attempt numbering: 1st reassessment is "Attempt 1", 2nd is "Attempt 2", etc.
2. **Submission Idempotency**:
   - Repeated submission of a completed reassessment returns `HTTP 400 Bad Request` ("Assessment has already been completed and cannot be resubmitted").
3. **Multiple Reassessment Attempts**:
   - Officers are permitted to undertake multiple successive reassessments over time as they complete additional modules.
   - Comparison endpoints support comparing Attempt $N$ against Baseline, or Attempt $N$ against Attempt $N-1$.
4. **Invalid Baseline Handling**:
   - If baseline assessment does not exist: `HTTP 404 Not Found`.
   - If baseline is still `IN_PROGRESS`: `HTTP 400 Bad Request` ("Baseline assessment must be completed before triggering a reassessment").
   - If officer attempts to reassess another officer's baseline: `HTTP 403 Forbidden`.

---

## 10. Implementation Steps Breakdown

```text
Step 1: Configuration & Schemas
 ├── Add reassessment comparison schemas to `app/schemas/assessment.py`
 └── Export schemas in `app/schemas/__init__.py`

Step 2: Service Layer (`app/services/assessment_service.py` & `reassessment_service.py`)
 ├── Implement `create_reassessment(db, baseline_id, request, current_user)`
 ├── Implement `get_reassessment_comparison(db, reassessment_id, baseline_id, current_user)`
 ├── Implement `list_reassessments_for_baseline(db, baseline_id, current_user)`
 └── Integrate learning context lookup from `recommendations` table

Step 3: Router Endpoints (`app/routers/assessments.py`)
 ├── `POST /api/v1/assessments/{baseline_id}/reassess`
 ├── `GET /api/v1/assessments/{reassessment_id}/comparison`
 └── `GET /api/v1/assessments/{baseline_id}/reassessments`

Step 4: Automated Testing Suite
 ├── Create `tests/test_reassessments.py` covering creation, comparison, RBAC, deltas, and edge cases
 └── Verify all 153 existing tests continue to pass (target >= 170 passing tests)

Step 5: Live PostgreSQL Verification
 └── Create `scratch/verify_phase_9_reassessment.py` covering full end-to-end closed loop
```

---

## 11. Testing Strategy

Create [`tests/test_reassessments.py`](file:///c:/SIH/backend/tests/test_reassessments.py) containing comprehensive automated test scenarios:
1. `test_create_reassessment_unauthenticated`: Rejection with HTTP 401.
2. `test_create_reassessment_other_officer_forbidden`: Officer A cannot reassess Officer B's baseline (HTTP 403).
3. `test_create_reassessment_in_progress_baseline_rejected`: Reassessment requires completed baseline (HTTP 400).
4. `test_create_reassessment_targets_baseline_gaps`: Questions correctly assigned to baseline gap competencies.
5. `test_baseline_assessment_remains_unmodified`: Baseline answers, results, and gaps are untouched after reassessment creation and submission.
6. `test_reassessment_comparison_positive_improvement`: Officer scores higher; delta is positive; gap resolves (`RESOLVED`).
7. `test_reassessment_comparison_partial_improvement`: One gap resolves, one persists (`PARTIALLY_CLOSED`).
8. `test_reassessment_comparison_no_improvement`: Officer scores identical; delta is zero; gap persists (`PERSISTENT`).
9. `test_reassessment_comparison_score_declined`: Officer scores lower; delta is negative; gap increases (`INCREASED`).
10. `test_reassessment_learning_context_correlation`: Preceding completed course is cited with non-causal correlation note.
11. `test_multiple_reassessment_attempts`: Officer undertakes Attempt 1, then Attempt 2; both preserved in history.
12. `test_reassessment_rbac_trainer_and_admin`: Trainer can view comparisons across officers; Trainer cannot submit.
13. `test_reassessment_rbac_sme_forbidden`: SME blocked from comparison and reassessment endpoints (HTTP 403).
14. `test_zero_schema_changes_and_16_tables`: Confirms database retains exactly 16 tables.

---

## 12. Verification Criteria & Deliverables

1. **Automated Test Results**: All existing 153 tests pass + all new Phase 9 tests pass.
2. **Schema Verification**: Table count verified at **strictly 16 tables** via SQLAlchemy inspector.
3. **Live Closed Loop Verification**: Live script execution demonstrating:
   $$\text{Baseline Assessment (50\%)} \rightarrow \text{Gap Identified} \rightarrow \text{Course Completed} \rightarrow \text{Reassessment (90\%)} \rightarrow \text{Gap RESOLVED (+40\% Delta)}$$
4. **Documentation**: Detailed `PHASE_9_REPORT.md` and updated walkthrough documentation.
