# StatKarmayogi — Phase 5 Implementation Report
## MCQ Generation & Prompt Engineering (RAG with Mistral LLM)

**Smart India Hackathon 2026**  
- **Problem Statement ID**: SIH26101  
- **Organization**: Ministry of Statistics and Programme Implementation (MoSPI)  
- **Theme**: Smart Education  
- **Phase**: Phase 5 — MCQ Generation & Prompt Engineering  
- **Status**: Completed & Fully Verified  

---

## 1. Files Created
1. `app/schemas/question.py`: Pydantic schemas for MCQ generation and retrieval:
   - `MCQGenerationItem`: Schema enforced on Mistral LLM structured output.
   - `MCQGenerationBatch`: Batch container for structured LLM response.
   - `QuestionGenerateRequest`: Request payload (`document_id`, `num_questions`, `difficulty`, `competency_id`).
   - `QuestionResponse`: Public representation of an MCQ entity.
   - `QuestionListResponse`: Paginated questions list wrapper.
2. `app/services/llm_service.py`: Mistral AI LLM orchestration service:
   - `LLMService.get_llm_client`: Returns `ChatMistralAI` configured with `mistral-large-latest` and temperature `0.2`.
   - `LLMService.build_system_prompt`: MoSPI domain framing enforcing strict factual grounding, explicit source chunk citation, 4 distinct options, and no invented facts.
   - `LLMService.build_user_prompt`: RAG prompt formatting retrieved chunks with explicit markers (`[CHUNK ID: {id}, PAGE: {page}]`) and constraints.
   - `LLMService.generate_mcqs_from_context`: Uses `with_structured_output(MCQGenerationBatch)` to invoke the model safely.
3. `app/services/question_service.py`: Business service orchestrating the RAG MCQ lifecycle:
   - `generate_questions`: Validates document status (`PROCESSED`), loads competency from PostgreSQL, executes ChromaDB vector search as the primary retriever, cross-references with PostgreSQL `document_chunks` for relational traceability, invokes LLM structured output, validates structural and attribution constraints, deduplicates within batch, and persists atomically.
   - `list_questions`: Filterable query supporting `document_id`, `status`, `competency_id`, `difficulty`, and pagination.
   - `get_question_by_id`: Fetches detailed question entity by ID.
4. `app/routers/questions.py`: FastAPI route handlers for questions endpoints:
   - `POST /api/v1/questions/generate` (Restricted to `TRAINER`, `ADMIN`).
   - `GET /api/v1/questions` (Restricted to `TRAINER`, `SME`, `ADMIN`).
   - `GET /api/v1/questions/{question_id}` (Restricted to `TRAINER`, `SME`, `ADMIN`).
5. `tests/test_questions.py`: Comprehensive test suite containing 18 unit and integration tests with zero-credit mock LLM and embeddings.
6. `scratch/verify_phase_5_mcq.py`: Live end-to-end verification script testing the full pipeline against PostgreSQL and ChromaDB.

---

## 2. Files Modified
1. `app/core/config.py`: Added `MISTRAL_LLM_MODEL: str = "mistral-large-latest"`, `MISTRAL_TEMPERATURE: float = 0.2`, `DEFAULT_MCQ_VOLUME: int = 5`, `MAX_MCQ_VOLUME: int = 20`.
2. `.env.example`: Documented Phase 5 configuration settings.
3. `app/schemas/__init__.py`: Exported question schemas.
4. `app/services/__init__.py`: Exported `LLMService` and `QuestionService`.
5. `app/routers/__init__.py`: Exported `questions_router`.
6. `app/main.py`: Registered `questions_router` under prefix `/api/v1`.
7. `backend/README.md`: Added Section 13 documenting Phase 5 architecture, endpoints, and updated test status.

---

## 3. Core Architectural Highlights & Compliance with Directives

### 1. ChromaDB as Primary Vector Retrieval Mechanism
- ChromaDB is used as the **primary vector retriever** for context selection.
- `VectorStoreService.similarity_search` is invoked with `query_embedding` and `where={"document_id": document_id}`.
- PostgreSQL `document_chunks` is used strictly for relational metadata, traceability, and integer chunk IDs.

### 2. Competency as a Generation Constraint
- When `competency_id` is supplied:
  - The competency's `name` and `description` are loaded directly from PostgreSQL `competencies`.
  - Inactive competencies are rejected (`HTTP 400 Bad Request`).
  - Competency metadata steers the ChromaDB semantic query vector and is injected into the LLM prompt as a generation constraint.
  - No unvalidated claims of "psychometric validation" or "automated alignment validation" are made.

### 3. Concrete Quality & Grounding Checks
- Non-empty question text ending with `'?'`.
- Exactly 4 distinct, non-empty options (`option_a`, `option_b`, `option_c`, `option_d`). Questions with duplicate options or non-distinct choices are filtered out.
- `correct_option` must strictly be one of `'A'`, `'B'`, `'C'`, or `'D'`.
- Mandatory educational explanation citing facts from the source text.

### 4. Explicit Source Chunk Attribution (No Post-Hoc Assignment)
- Every chunk in the RAG prompt is tagged: `[CHUNK ID: {id}, PAGE: {page}]`.
- The LLM explicitly returns `source_chunk_id` for every question.
- The backend validates that `source_chunk_id` was in the set of retrieved chunks before persisting `source_chunk_id` and `source_page`.
- Questions referencing non-retrieved or hallucinated chunk IDs are rejected prior to persistence.

### 5. Strict Grounding (No External Facts)
- The system prompt instructs the model to rely solely and exclusively on facts directly stated in the context chunks.
- If insufficient facts exist, the model is forbidden from extrapolating or inventing facts.

### 6. Batch Duplicate Detection
- Intra-batch duplicate detection normalizes `question_text` and filters out duplicate items before database persistence.

### 7. Atomic Single-Transaction Persistence
- Generated questions are added to the session with `status = QuestionStatus.PENDING_REVIEW`.
- `document.generation_count` is incremented by the number of persisted questions.
- Both operations are committed together in a single atomic database transaction.

### 8. Phase 6 Boundary Preserved
- All generated questions are persisted with `status = PENDING_REVIEW`.
- Zero SME review queue or approval/rejection endpoints were implemented, cleanly preserving the Phase 6 boundary.

### 9. Approved Technical Stack Only
- `langchain-mistralai` (`ChatMistralAI`), `chromadb`, `FastAPI`, `SQLAlchemy 2.x`, and `Pydantic v2`.
- Zero database schema alterations were required.

---

## 4. API Endpoints Added

| Method | Endpoint | Authorized Roles | Description | Status Code |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/questions/generate` | `TRAINER`, `ADMIN` | Trigger RAG MCQ generation from a processed document | `201 Created` |
| `GET` | `/api/v1/questions` | `TRAINER`, `SME`, `ADMIN` | Filter & paginate generated MCQs (`document_id`, `status`, etc.) | `200 OK` |
| `GET` | `/api/v1/questions/{id}` | `TRAINER`, `SME`, `ADMIN` | Retrieve single question details and attribution | `200 OK` |

---

## 5. Verification Results

### Automated Pytest Suite
```
======================= 81 passed, 2 warnings in 6.41s ========================
```
- **Foundation & Health**: 5 passed
- **Relational Models & Schema (15 Tables)**: 9 passed
- **Authentication & RBAC**: 24 passed
- **Document Ingestion & ChromaDB**: 25 passed
- **Phase 5 MCQ Generation & RAG**: 18 passed
- **Total**: 81 passed (100% pass rate)
- **Credit Consumption**: 0 API credits used (mock embeddings & mock LLM output handlers).

### Live Verification Script (`scratch/verify_phase_5_mcq.py`)
- Ingested multi-page MoSPI Annual Survey of Industries (ASI) PDF document.
- Verified 3 chunks indexed in ChromaDB and PostgreSQL.
- Created competency: "ASI Survey Methodology & Classification".
- Successfully generated 3 MCQs with:
  - `status == PENDING_REVIEW`
  - Valid `source_chunk_id` and `source_page` matched to database chunks
  - 4 distinct options with valid key `'A'`
  - Atomically updated `document.generation_count = 3`
- Verified `GET /api/v1/questions?document_id=...` returned all 3 questions.
- Verified `OFFICER` role receives `403 Forbidden` on both generate and list endpoints.

---

## 6. Readiness for Phase 6

Phase 5 is complete, fully verified, and ready for:
**Phase 6 — Human-in-the-Loop SME Review & Validation Queue**
- SME review queue endpoints (`GET /api/v1/reviews/pending`).
- Review action endpoints (`POST /api/v1/reviews/{question_id}/approve`, `reject`, `edit`).
- Populating the `question_reviews` relational table.
- Status transitions (`PENDING_REVIEW` $\rightarrow$ `APPROVED` / `REJECTED` / `NEEDS_REVISION`).
