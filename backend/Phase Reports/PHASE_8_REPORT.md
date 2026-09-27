# StatKarmayogi — Phase 8 Implementation Report
## iGOT Learning Pathways & Course Recommendations

**Smart India Hackathon 2026**  
- **Problem Statement ID**: SIH26101  
- **Organization**: Ministry of Statistics and Programme Implementation (MoSPI)  
- **Theme**: Smart Education  
- **Phase**: Phase 8 — iGOT Learning Pathways & Course Recommendations  
- **Status**: Completed & Fully Verified  

---

## 1. Objective

Phase 8 completes the transition from diagnostic competency assessment into the adaptive learning phase of the closed learning loop:

$$\text{Assess (Phase 7)} \longrightarrow \text{Skill Gaps (Phase 7)} \longrightarrow \mathbf{iGOT\ Recommendations\ (Phase\ 8)} \longrightarrow \text{Learn} \longrightarrow \text{Reassess (Phase 9)}$$

Key accomplishments:
- Connects Phase 7 persisted `skill_gaps` records directly to an iGOT-aligned prototype course catalogue.
- Executes a 100% deterministic, zero-AI matching algorithm directly against PostgreSQL `Course` and `CourseCompetency` records to calculate match scores and gap priorities.
- Treats the `IGOTAdapter` interface as an integration boundary, avoiding artificial invocation in core deterministic matching while supporting future production migration.
- Generates transparent, template-based, explainable recommendation reasons citing the exact diagnostic basis.
- Provides safe recommendation regeneration that strictly preserves officer learning history (`STARTED`, `COMPLETED`, and `DISMISSED` states), applying the global cap of 6 solely to the current active recommendation set.
- Enforces a strict recommendation status state machine (`RECOMMENDED` $\rightarrow$ `STARTED` $\rightarrow$ `COMPLETED` and `RECOMMENDED` $\rightarrow$ `DISMISSED`, with terminal protection).
- Maintains safe transaction boundaries: assessment submission commits diagnostic results first, and recommendation generation runs in an isolated post-commit block. Recommendation failure never invalidates or rolls back a completed assessment.
- Reuses and extends existing project RBAC mechanisms (`require_roles`, `get_current_user`, `RoleName`) without introducing any parallel authorization system.
- Zero dead course URLs: course URLs point to implemented routes or are null. Zero `is_external` columns or fields.
- Total PostgreSQL table count remains **exactly 16 tables** with **zero migrations**.

---

## 2. Existing Schema Reused & Confirmation of ZERO Schema Changes

In accordance with the project directives:
- Reused existing PostgreSQL tables: `courses`, `course_competencies`, `recommendations`, `skill_gaps`, `assessments`, `competencies`, `users`.
- Reused existing PostgreSQL enums:
  - `recommendation_status_enum`: `['RECOMMENDED', 'STARTED', 'COMPLETED', 'DISMISSED']`
  - `gap_level_enum`: `['HIGH', 'MEDIUM', 'LOW']`
- **Zero database migrations, zero column modifications, zero enum changes, and zero DDL alterations** were executed.
- `is_external` was completely excluded from models, schemas, and database tables.
- Database table count was inspected and confirmed at **exactly 16 tables**.

---

## 3. Files Created / Modified

### Files Created:
1. `app/integrations/igot_adapter.py`:
   - `BaseIGOTAdapter`: Abstract interface defining `get_courses` and `get_course_by_id`.
   - `MockIGOTAdapter`: Local implementation with in-memory prototype catalogue (`v1-prototype`), zero external network calls, and zero fictional external domains.
2. `app/db/seed_courses.py`:
   - `seed_courses(db)`: Idempotent seeding function for 6 prototype courses. Only explicitly verified course-to-competency mappings (ASI, IIP, NAS, SSD) are seeded with curated prototype relevance scores (`0.95`, `0.90`). Courses with no catalogue match (FPOS, DAP) remain safely unmapped pending SME alignment. Zero automatic fallback is permitted.

3. `app/schemas/course.py`:
   - `CourseCompetencyResponse`: Course-to-competency link schema.
   - `CourseResponse`: Base course attributes (no `is_external`).
   - `CourseDetailResponse`: Extended schema with linked competencies.
   - `CourseListResponse`: Paginated listing schema.
4. `app/schemas/recommendation.py`:
   - `RecommendationStatusUpdateRequest`: Payload for status transitions.
   - `RecommendationResponse`: Detailed explainable recommendation item.
   - `RecommendationListResponse`: Paginated list of recommendations.
   - `LearningPathwayResponse`: Aggregated learning pathway.
5. `app/services/recommendation_service.py`:
   - `generate_recommendations`: Deterministic matching, reason generation, active cap enforcement, and history-preserving reconciliation.
   - `list_assessment_recommendations`: Assessment-specific recommendation query.
   - `list_recommendations`: Cross-assessment listing with filters.
   - `get_recommendation`: Single recommendation lookup with RBAC.
   - `update_recommendation_status`: Status transition validation and state machine enforcement.
6. `app/routers/courses.py`:
   - `GET /api/v1/courses`: Catalogue listing and filtering.
   - `GET /api/v1/courses/{course_id}`: Course detail with competency mappings.
7. `app/routers/recommendations.py`:
   - `POST /api/v1/assessments/{assessment_id}/recommendations`: Generate/regenerate recommendations.
   - `GET /api/v1/assessments/{assessment_id}/recommendations`: Assessment recommendations.
   - `GET /api/v1/recommendations`: Cross-assessment listing.
   - `GET /api/v1/recommendations/{recommendation_id}`: Single recommendation detail.
   - `PATCH /api/v1/recommendations/{recommendation_id}/status`: Status transition.
8. `tests/test_courses.py`: 6 automated tests covering catalogue browsing, filtering, details, RBAC, and valid URL checks.
9. `tests/test_recommendations.py`: 19 automated tests covering security, deterministic scoring, state machine, idempotency, submission integration, and database constraints.
10. `scratch/verify_phase_8_recommendations.py`: 12-step end-to-end live PostgreSQL verification script.

### Files Modified:
1. `app/core/config.py`: Added Phase 8 constants (`MAX_RECOMMENDATIONS_PER_GAP = 2`, `MAX_TOTAL_ACTIVE_RECOMMENDATIONS = 6`, `IGOT_ADAPTER_TYPE = "mock"`, `MOCK_IGOT_CATALOGUE_VERSION = "v1-prototype"`).
2. `app/integrations/__init__.py`: Exported `BaseIGOTAdapter` and `MockIGOTAdapter`.
3. `app/db/seed.py`: Added `seed_all` hook invoking `seed_courses`.
4. `app/schemas/__init__.py`: Exported course and recommendation schemas.
5. `app/services/__init__.py`: Exported `RecommendationService`.
6. `app/services/assessment_service.py`: Added safe post-commit recommendation generation hook in `submit_assessment`.
7. `app/routers/__init__.py`: Exported `courses_router` and `recommendations_router`.
8. `app/main.py`: Mounted `courses_router` and `recommendations_router` under `/api/v1`.
9. `backend/README.md`: Documented Phase 8 endpoints, architecture, test results, and next phase.

---

## 4. Deterministic Scoring & Matching Rules

### 1. Gap Multipliers & Priority:
- `GapLevel.HIGH` $\implies \text{gap\_multiplier} = 1.00$, $\text{priority} = 1$
- `GapLevel.MEDIUM` $\implies \text{gap\_multiplier} = 0.85$, $\text{priority} = 2$
- `GapLevel.LOW` $\implies \text{gap\_multiplier} = 0.70$, $\text{priority} = 3$

### 2. Match Score Formula:
$$\text{match\_score} = \operatorname{round}\left(\text{float}(\text{relevance\_score}) \times \text{gap\_multiplier} \times 100, 2\right)$$

### 3. Tie-Breaking Order:
1. `priority ASC` (High severity gaps first)
2. `match_score DESC` (Highest match score first)
3. `relevance_score DESC` (Highest domain relevance first)
4. `course_id ASC` (Stable primary-key tie-breaker)

### 4. Recommendation Limits:
- **Per-Gap Limit**: At most 2 courses per skill gap.
- **Global Active Cap**: At most 6 active recommendations (`status = RECOMMENDED`).
- **Historical Rows**: `STARTED`, `COMPLETED`, and `DISMISSED` records do not count toward the active cap. Total rows in the database for an assessment may legitimately exceed 6.

### 5. Template-Based Explainable Reason:
```text
"Recommended because your assessment score in {competency_name} was {score_percentage}%, "
"identified as a {gap_level} priority skill gap. This course has a {relevance_pct}% domain "
"relevance to this competency, resulting in a match score of {match_score}%."
```

---

## 5. Status State Machine Enforced

| From State | Allowed Target States | Rejected Target States (HTTP 400) | Notes |
| :--- | :--- | :--- | :--- |
| `RECOMMENDED` | `STARTED`, `DISMISSED` | `COMPLETED`, `RECOMMENDED` | Cannot complete before starting |
| `STARTED` | `COMPLETED` | `RECOMMENDED`, `DISMISSED`, `STARTED` | Cannot dismiss after starting |
| `COMPLETED` | *None* (Terminal) | `RECOMMENDED`, `STARTED`, `DISMISSED` | Completed is terminal |
| `DISMISSED` | *None* (Terminal) | `RECOMMENDED`, `STARTED`, `COMPLETED` | Dismissed is terminal |

---

## 6. RBAC Permission Matrix

| Role | Browse Courses | View Own Recs | View Others' Recs | Generate/Regen Recs | Update Rec Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **OFFICER** | Yes | Yes | No (403) | Yes (Own only) | Yes (Own only) |
| **TRAINER** | Yes | N/A | Yes | No (403) | No (403) |
| **ADMIN** | Yes | Yes | Yes | Yes | Yes |
| **SME** | Yes (Read-only) | No (403) | No (403) | No (403) | No (403) |
| **Unauthenticated** | No (401) | No (401) | No (401) | No (401) | No (401) |

---

## 7. Automated Test Suite Results

```text
============================= test session starts =============================
platform win32 -- Python 3.14.5, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\SIH\backend
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.13.0, langsmith-0.8.5
collected 150 items

tests\test_assessments.py ............................                   [ 18%]
tests\test_auth.py .............................                         [ 38%]
tests\test_courses.py ......                                             [ 42%]
tests\test_documents.py ........................                         [ 58%]
tests\test_health.py .....                                               [ 61%]
tests\test_models.py ..........                                          [ 68%]
tests\test_questions.py .............................                    [ 87%]
tests\test_recommendations.py ...................                        [100%]

======================= 150 passed, 2 warnings in 7.88s =======================
```

- **Existing Tests (Phases 1–7)**: 125 passed
- **New Phase 8 Tests**: 25 passed
- **Total Passing Tests**: **150 passed (100% pass rate)**

---

## 8. Live PostgreSQL Verification Results

Executed `python -m scratch.verify_phase_8_recommendations`:
- [x] Step 1: Pre-verified active competencies in PostgreSQL.
- [x] Step 2: Seeded prototype courses and roles idempotently.
- [x] Step 3: Verified all course URLs are safe/null. Zero dead or fake URLs. Zero `is_external` columns.
- [x] Step 4: Generated test users and JWT tokens across roles.
- [x] Step 5: Created completed assessment with skill gaps.
- [x] Step 6: Generated recommendations via API.
- [x] Step 7: Verified deterministic match scores and explainable template reasons.
- [x] Step 8: Verified full state machine transitions and terminal protection on COMPLETED/DISMISSED.
- [x] Step 9: Verified regeneration preserves learning history.
- [x] Step 10: Verified RBAC restrictions across Officer, Trainer, Admin, and SME.
- [x] Step 11: Verified 100% score assessment produces empty recommendation list cleanly.
- [x] Step 12: Verified total PostgreSQL table count is **EXACTLY 16 TABLES**.

---

## 9. Conclusion & Phase 9 Readiness

Phase 8 is **100% complete, fully tested, and verified** against live PostgreSQL. The implementation establishes a solid, explainable, and resilient foundation for **Phase 9: Officer Reassessment & Closed-Loop Learning Progression**.
