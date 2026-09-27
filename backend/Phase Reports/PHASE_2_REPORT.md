# StatKarmayogi — Phase 2 Implementation Report: Database Schema

**Smart India Hackathon 2026**  
- **Problem Statement ID**: SIH26101  
- **Organization**: Ministry of Statistics and Programme Implementation (MoSPI)  
- **Status**: Phase 2 Completed & Fully Verified  

---

## 1. Models Created
Exactly 15 SQLAlchemy 2.x declarative models were created under `app/models/`, one file per entity, inheriting from `app.db.base.Base`:

| # | Model Class | Table Name | File Location | Key Fields |
|---|---|---|---|---|
| 1 | `Role` | `roles` | `app/models/role.py` | `id`, `name` |
| 2 | `User` | `users` | `app/models/user.py` | `id`, `name`, `email`, `password_hash`, `role_id`, `department`, `designation`, `is_active`, `created_at`, `updated_at` |
| 3 | `Competency` | `competencies` | `app/models/competency.py` | `id`, `code`, `name`, `description`, `category`, `is_active`, `created_at`, `updated_at` |
| 4 | `Document` | `documents` | `app/models/document.py` | `id`, `uploaded_by`, `filename`, `file_type`, `file_path`, `status`, `processing_error`, `generation_count`, `created_at`, `updated_at` |
| 5 | `DocumentChunk` | `document_chunks` | `app/models/document_chunk.py` | `id`, `document_id`, `chunk_index`, `page_number`, `content_hash`, `chroma_id`, `created_at` |
| 6 | `Question` | `questions` | `app/models/question.py` | `id`, `document_id`, `competency_id`, `question_text`, `option_a`, `option_b`, `option_c`, `option_d`, `correct_option`, `difficulty`, `explanation`, `source_page`, `source_chunk_id`, `generation_model`, `status`, `created_by`, `created_at`, `updated_at` |
| 7 | `QuestionReview` | `question_reviews` | `app/models/question_review.py` | `id`, `question_id`, `reviewer_id`, `action`, `comment`, `created_at` |
| 8 | `Assessment` | `assessments` | `app/models/assessment.py` | `id`, `officer_id`, `title`, `status`, `total_questions`, `total_correct`, `score_percentage`, `started_at`, `completed_at` |
| 9 | `AssessmentQuestion`| `assessment_questions`| `app/models/assessment_question.py`| `id`, `assessment_id`, `question_id`, `question_order` |
| 10| `Answer` | `answers` | `app/models/answer.py` | `id`, `assessment_id`, `question_id`, `selected_option`, `is_correct`, `answered_at` |
| 11| `CompetencyResult`| `competency_results` | `app/models/competency_result.py` | `id`, `assessment_id`, `competency_id`, `questions_attempted`, `questions_correct`, `score_percentage`, `proficiency_level`, `created_at` |
| 12| `SkillGap` | `skill_gaps` | `app/models/skill_gap.py` | `id`, `assessment_id`, `competency_id`, `score_percentage`, `gap_level`, `created_at` |
| 13| `Course` | `courses` | `app/models/course.py` | `id`, `igot_course_id`, `title`, `description`, `provider`, `language`, `difficulty`, `duration_minutes`, `course_url`, `is_public`, `is_active`, `source`, `created_at`, `updated_at` |
| 14| `CourseCompetency`| `course_competencies` | `app/models/course_competency.py` | `id`, `course_id`, `competency_id`, `relevance_score`, `created_at` |
| 15| `Recommendation` | `recommendations` | `app/models/recommendation.py` | `id`, `officer_id`, `assessment_id`, `competency_id`, `course_id`, `priority`, `match_score`, `reason`, `status`, `created_at` |

Shared domain enums were defined in `app/models/enums.py`:
- `RoleName` (`TRAINER`, `SME`, `OFFICER`, `ADMIN`)
- `DocumentStatus` (`UPLOADED`, `PROCESSING`, `PROCESSED`, `FAILED`)
- `QuestionDifficulty` (`EASY`, `MEDIUM`, `HARD`)
- `QuestionStatus` (`PENDING_REVIEW`, `APPROVED`, `REJECTED`)
- `ReviewAction` (`APPROVE`, `REJECT`)
- `AssessmentStatus` (`IN_PROGRESS`, `COMPLETED`)
- `ProficiencyLevel` (`BEGINNER`, `DEVELOPING`, `PROFICIENT`, `ADVANCED`)
- `GapLevel` (`HIGH`, `MEDIUM`, `LOW`)
- `RecommendationStatus` (`RECOMMENDED`, `STARTED`, `COMPLETED`, `DISMISSED`)

---

## 2. Relationships Created
- `roles` $\xrightarrow{1:M}$ `users` (`users.role_id` $\rightarrow$ `roles.id`, `ondelete="RESTRICT"`)
- `users` $\xrightarrow{1:M}$ `documents` (`documents.uploaded_by` $\rightarrow$ `users.id`, `ondelete="RESTRICT"`)
- `documents` $\xrightarrow{1:M}$ `document_chunks` (`document_chunks.document_id` $\rightarrow$ `documents.id`, `ondelete="CASCADE"`, cascade delete-orphan)
- `documents` $\xrightarrow{1:M}$ `questions` (`questions.document_id` $\rightarrow$ `documents.id`, `ondelete="RESTRICT"`)
- `competencies` $\xrightarrow{1:M}$ `questions` (`questions.competency_id` $\rightarrow$ `competencies.id`, `ondelete="RESTRICT"`)
- `document_chunks` $\xrightarrow{1:M}$ `questions` (`questions.source_chunk_id` $\rightarrow$ `document_chunks.id`, `ondelete="SET NULL"`)
- `users` $\xrightarrow{1:M}$ `questions` (`questions.created_by` $\rightarrow$ `users.id`, `ondelete="RESTRICT"`)
- `questions` $\xrightarrow{1:M}$ `question_reviews` (`question_reviews.question_id` $\rightarrow$ `questions.id`, `ondelete="CASCADE"`)
- `users` $\xrightarrow{1:M}$ `question_reviews` (`question_reviews.reviewer_id` $\rightarrow$ `users.id`, `ondelete="RESTRICT"`)
- `users` $\xrightarrow{1:M}$ `assessments` (`assessments.officer_id` $\rightarrow$ `users.id`, `ondelete="RESTRICT"`)
- `assessments` $\xrightarrow{1:M}$ `assessment_questions` (`assessment_questions.assessment_id` $\rightarrow$ `assessments.id`, `ondelete="CASCADE"`)
- `questions` $\xrightarrow{1:M}$ `assessment_questions` (`assessment_questions.question_id` $\rightarrow$ `questions.id`, `ondelete="RESTRICT"`)
- `assessments` $\xrightarrow{1:M}$ `answers` (`answers.assessment_id` $\rightarrow$ `assessments.id`, `ondelete="CASCADE"`)
- `questions` $\xrightarrow{1:M}$ `answers` (`answers.question_id` $\rightarrow$ `questions.id`, `ondelete="RESTRICT"`)
- `assessments` $\xrightarrow{1:M}$ `competency_results` (`competency_results.assessment_id` $\rightarrow$ `assessments.id`, `ondelete="CASCADE"`)
- `competencies` $\xrightarrow{1:M}$ `competency_results` (`competency_results.competency_id` $\rightarrow$ `competencies.id`, `ondelete="RESTRICT"`)
- `assessments` $\xrightarrow{1:M}$ `skill_gaps` (`skill_gaps.assessment_id` $\rightarrow$ `assessments.id`, `ondelete="CASCADE"`)
- `competencies` $\xrightarrow{1:M}$ `skill_gaps` (`skill_gaps.competency_id` $\rightarrow$ `competencies.id`, `ondelete="RESTRICT"`)
- `courses` $\xrightarrow{1:M}$ `course_competencies` (`course_competencies.course_id` $\rightarrow$ `courses.id`, `ondelete="CASCADE"`)
- `competencies` $\xrightarrow{1:M}$ `course_competencies` (`course_competencies.competency_id` $\rightarrow$ `competencies.id`, `ondelete="RESTRICT"`)
- `users` $\xrightarrow{1:M}$ `recommendations` (`recommendations.officer_id` $\rightarrow$ `users.id`, `ondelete="RESTRICT"`)
- `assessments` $\xrightarrow{1:M}$ `recommendations` (`recommendations.assessment_id` $\rightarrow$ `assessments.id`, `ondelete="CASCADE"`)
- `competencies` $\xrightarrow{1:M}$ `recommendations` (`recommendations.competency_id` $\rightarrow$ `competencies.id`, `ondelete="RESTRICT"`)
- `courses` $\xrightarrow{1:M}$ `recommendations` (`recommendations.course_id` $\rightarrow$ `courses.id`, `ondelete="RESTRICT"`)

---

## 3. Constraints Created
- **Unique Constraints (Single-column)**:
  - `roles.name`: UNIQUE
  - `users.email`: UNIQUE
  - `competencies.code`: UNIQUE
  - `courses.igot_course_id`: UNIQUE
- **Composite Unique Constraints**:
  - `document_chunks`: `uq_document_chunk_index` (`document_id`, `chunk_index`)
  - `course_competencies`: `uq_course_competency` (`course_id`, `competency_id`)
  - `assessment_questions`: `uq_assessment_question` (`assessment_id`, `question_id`)
  - `assessment_questions`: `uq_assessment_question_order` (`assessment_id`, `question_order`)
  - `answers`: `uq_assessment_question_answer` (`assessment_id`, `question_id`)
  - `competency_results`: `uq_assessment_competency_result` (`assessment_id`, `competency_id`)
  - `skill_gaps`: `uq_assessment_competency_gap` (`assessment_id`, `competency_id`)

---

## 4. Indexes Created
- `ix_roles_name` on `roles(name)`
- `ix_users_email` on `users(email)`
- `ix_users_role_id` on `users(role_id)`
- `ix_competencies_code` on `competencies(code)`
- `ix_documents_uploaded_by` on `documents(uploaded_by)`
- `ix_documents_status` on `documents(status)`
- `ix_document_chunks_document_id` on `document_chunks(document_id)`
- `ix_document_chunks_chroma_id` on `document_chunks(chroma_id)`
- `ix_document_chunks_content_hash` on `document_chunks(content_hash)`
- `ix_questions_document_id` on `questions(document_id)`
- `ix_questions_competency_id` on `questions(competency_id)`
- `ix_questions_created_by` on `questions(created_by)`
- `ix_questions_difficulty` on `questions(difficulty)`
- `ix_questions_source_chunk_id` on `questions(source_chunk_id)`
- `ix_questions_status` on `questions(status)`
- `ix_question_reviews_question_id` on `question_reviews(question_id)`
- `ix_question_reviews_reviewer_id` on `question_reviews(reviewer_id)`
- `ix_assessments_officer_id` on `assessments(officer_id)`
- `ix_assessments_status` on `assessments(status)`
- `ix_assessment_questions_assessment_id` on `assessment_questions(assessment_id)`
- `ix_assessment_questions_question_id` on `assessment_questions(question_id)`
- `ix_answers_assessment_id` on `answers(assessment_id)`
- `ix_answers_question_id` on `answers(question_id)`
- `ix_competency_results_assessment_id` on `competency_results(assessment_id)`
- `ix_competency_results_competency_id` on `competency_results(competency_id)`
- `ix_skill_gaps_assessment_id` on `skill_gaps(assessment_id)`
- `ix_skill_gaps_competency_id` on `skill_gaps(competency_id)`
- `ix_courses_igot_course_id` on `courses(igot_course_id)`
- `ix_course_competencies_course_id` on `course_competencies(course_id)`
- `ix_course_competencies_competency_id` on `course_competencies(competency_id)`
- `ix_recommendations_officer_id` on `recommendations(officer_id)`
- `ix_recommendations_assessment_id` on `recommendations(assessment_id)`
- `ix_recommendations_competency_id` on `recommendations(competency_id)`
- `ix_recommendations_course_id` on `recommendations(course_id)`
- `ix_recommendations_status` on `recommendations(status)`

---

## 5. Migration Generated
- **Revision ID**: `02255fcc9e4b`
- **File**: `backend/alembic/versions/02255fcc9e4b_create_initial_schema.py`
- **Tables Handled**: All 15 application tables.
- **Bi-directional Capability**: Tested and verified for both `upgrade head` and `downgrade base` (with full cleanup of custom PostgreSQL enum types to prevent orphaned database types).

---

## 6. Seed Mechanism Created
- **Script**: `app/db/seed.py` (runnable via `python -m app.db.seed`)
- **Seeded Entities**: Exactly the 4 system roles (`TRAINER`, `SME`, `OFFICER`, `ADMIN`).
- **Safety**: Fully idempotent. Verified running twice sequentially; the second run detected all 4 existing roles and added 0 new records.
- **Boundaries**: No fake users, no fake competencies, no fake courses, and no fake questions were seeded.

---

## 7. Tests Executed & Results
Comprehensive test suite in `tests/test_models.py` (alongside existing `tests/test_health.py`):
```text
tests/test_health.py::test_app_import PASSED                             [  6%]
tests/test_health.py::test_read_root PASSED                              [ 13%]
tests/test_health.py::test_health_check PASSED                           [ 20%]
tests/test_health.py::test_settings_loaded PASSED                        [ 26%]
tests/test_health.py::test_database_configuration PASSED                 [ 33%]
tests/test_models.py::test_all_15_tables_exist_in_metadata PASSED        [ 40%]
tests/test_models.py::test_all_15_tables_exist_in_database PASSED        [ 46%]
tests/test_models.py::test_role_seed_creates_exactly_4_roles PASSED      [ 53%]
tests/test_models.py::test_user_email_unique_constraint PASSED           [ 60%]
tests/test_models.py::test_competency_code_unique_constraint PASSED      [ 66%]
tests/test_models.py::test_course_igot_id_unique_constraint PASSED       [ 73%]
tests/test_models.py::test_course_competency_unique_constraint PASSED    [ 80%]
tests/test_models.py::test_assessment_question_unique_constraint PASSED  [ 86%]
tests/test_models.py::test_answer_unique_constraint PASSED               [ 93%]
tests/test_models.py::test_full_relational_lifecycle PASSED              [100%]

============================= 15 passed in 0.78s ==============================
```

---

## 8. Migration & Database Verification Results
- **`Base.metadata.tables` Verification**:
  ```python
  python -c "from app.db.base import Base; print(sorted(Base.metadata.tables.keys()))"
  ```
  **Output**:
  `['answers', 'assessment_questions', 'assessments', 'competencies', 'competency_results', 'course_competencies', 'courses', 'document_chunks', 'documents', 'question_reviews', 'questions', 'recommendations', 'roles', 'skill_gaps', 'users']`
- **PostgreSQL Database Inspection**:
  ```text
  Tables in PostgreSQL: ['alembic_version', 'answers', 'assessment_questions', 'assessments', 'competencies', 'competency_results', 'course_competencies', 'courses', 'document_chunks', 'documents', 'question_reviews', 'questions', 'recommendations', 'roles', 'skill_gaps', 'users']
  ```
- **Alembic Status**:
  `alembic current` confirms `02255fcc9e4b (head)`.

---

## 9. Design Decisions Made
1. **Foreign Key Delete Protection (`RESTRICT` vs `CASCADE`)**:
   - `RESTRICT` was explicitly applied to `users.role_id`, `assessments.officer_id`, `question_reviews.reviewer_id`, `questions.created_by`, and `documents.uploaded_by` to ensure historical assessment records, audit trails, and accountability cannot be accidentally deleted if a user record is removed.
   - `CASCADE` was applied only to tightly coupled owned child entities: `document_chunks` (owned by `documents`), `assessment_questions`, `answers`, `competency_results`, and `skill_gaps` (owned by `assessments`), and `question_reviews` (owned by `questions`).
   - `SET NULL` was applied to `questions.source_chunk_id` so that question text and evaluation records remain intact even if chunk embeddings are regenerated.
2. **PostgreSQL Enum Downgrade Handling**:
   - Alembic autogenerated migrations do not drop custom PostgreSQL enum types on table drop by default. We added explicit `sa.Enum.drop(..., checkfirst=True)` calls in `downgrade()` to guarantee clean downgrades to empty databases without type collisions.
3. **Idempotent Role Seeding**:
   - Built with transactional queries checking existing role names prior to insertion to avoid unique constraint violations on re-execution.

---

## 10. Unresolved Issues
- None. All 15 entities, relationships, constraints, indexes, migration scripts, tests, and seed mechanisms are verified.

---

**Confirmation**: No later-phase functionality (authentication endpoints, password hashing, JWT tokens, RAG pipelines, ChromaDB vector stores, LLM generation, or frontend UI) was implemented.
