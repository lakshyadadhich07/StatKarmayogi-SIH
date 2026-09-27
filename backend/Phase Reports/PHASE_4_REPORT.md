# StatKarmayogi — Phase 4 Implementation Report (Corrected)
## Document Ingestion, LangChain PyPDFLoader, Recursive Text Splitting, Mistral Embeddings & ChromaDB

**Smart India Hackathon 2026**  
- **Problem Statement ID**: SIH26101  
- **Organization**: Ministry of Statistics and Programme Implementation (MoSPI)  
- **Phase**: Phase 4 — Document Ingestion & Vector Indexing  
- **Status**: Completed & Fully Verified  

---

## 1. Files Created
1. `app/services/embedding_service.py`: Mistral AI embeddings service wrapping `MistralAIEmbeddings` from `langchain-mistralai`. Dynamically accommodates model dimensionality without hardcoding vector lengths, validates API key presence, and shields credentials from logs.
2. `app/services/vector_store.py`: Persistent ChromaDB management service for client initialization, collection lifecycle (`statkarmayogi_chunks`), deterministic vector upsertion, semantic similarity retrieval, and explicit two-system failure compensation.
3. `scratch/verify_phase_4_rag.py`: Comprehensive 13-step manual verification script executing against live PostgreSQL and ChromaDB.

---

## 2. Files Modified
1. `requirements.txt`: Added `langchain>=0.3.0`, `langchain-community>=0.3.0`, `langchain-text-splitters>=0.3.0`, `langchain-mistralai>=0.2.0`, `chromadb>=0.5.0`.
2. `app/core/config.py`: Added `MISTRAL_API_KEY`, `MISTRAL_EMBEDDING_MODEL` (`mistral-embed`), `CHROMA_PERSIST_DIRECTORY` (`storage/chroma`), and `CHROMA_COLLECTION_NAME` (`statkarmayogi_chunks`) to `Settings`.
3. `.env.example`: Documented new environment variables for Mistral AI and ChromaDB.
4. `backend/.gitignore`: Added `storage/chroma/` to prevent committing vector databases.
5. `app/services/document_parser.py`: Replaced direct `pypdf` reading with LangChain `PyPDFLoader` (`load_pdf_with_langchain`), normalizing page metadata to 1-indexed integers. Utilized `python-pptx` solely as a non-AI format parser to produce standard LangChain `Document` objects.
6. `app/services/document_chunker.py`: Replaced custom character slicing with LangChain's `RecursiveCharacterTextSplitter`, preserving document structure across paragraphs and lines while calculating deterministic SHA-256 `content_hash` and formatting traceable `chroma_id` values.
7. `app/services/document_service.py`: Orchestrated the LangChain $\rightarrow$ Mistral Embeddings $\rightarrow$ ChromaDB $\rightarrow$ PostgreSQL pipeline with explicit failure compensation (purging ChromaDB vectors if PostgreSQL commit fails) and synchronized deletion.
8. `app/schemas/document.py`: Added `DocumentSearchRequest` and `DocumentSearchResult` schemas.
9. `app/schemas/__init__.py`: Exported new search schemas.
10. `app/services/__init__.py`: Exported `EmbeddingService` and `VectorStoreService`.
11. `app/routers/documents.py`: Added authenticated semantic retrieval endpoint `POST /api/v1/documents/search`.
12. `tests/test_documents.py`: Re-architected with `MockMistralEmbeddings` and isolated temporary ChromaDB storage, adding tests for failure compensation, vector retrieval, and `chroma_id` population.
13. `backend/README.md`: Documented LangChain RAG ingestion, Mistral Embeddings, ChromaDB, and testing.

---

## 3. Dependencies Added
- `langchain>=0.3.0` & `langchain-core`: Foundation document interfaces and abstractions.
- `langchain-community>=0.3.0`: Document loaders including `PyPDFLoader`.
- `langchain-text-splitters>=0.3.0`: `RecursiveCharacterTextSplitter`.
- `langchain-mistralai>=0.2.0`: Official Mistral AI integration (`MistralAIEmbeddings`).
- `chromadb>=0.5.0`: Persistent local vector database.
- `pypdf>=4.0.0` & `python-pptx>=1.0.0`: Required underlying document format parsers.

*No alternative vector databases (FAISS, Pinecone, Weaviate, Qdrant) or alternative embedding models (HuggingFace, sentence-transformers, OpenAI) were introduced.*

---

## 4. Existing Functionality Preserved
1. FastAPI app foundation, middleware, CORS, and health checks.
2. Complete authentication system (Argon2id password hashing, JWT creation/verification).
3. Role-Based Access Control (`require_roles(RoleName.TRAINER, RoleName.ADMIN)` for uploads).
4. File extension validation (`.pdf`, `.pptx`).
5. MIME type validation.
6. File size validation (`MAX_UPLOAD_SIZE_MB = 20`, returning `HTTP 413 Content Too Large`).
7. Filename sanitization and directory traversal prevention (`sanitize_filename`).
8. Local filesystem storage under `storage/documents/{uuid}_{filename}`.
9. PostgreSQL 15-table relational schema (no migrations needed).
10. Document status lifecycle (`UPLOADED` $\rightarrow$ `PROCESSING` $\rightarrow$ `PROCESSED` or `FAILED`).
11. Document listing (`GET /api/v1/documents`).
12. Document detail (`GET /api/v1/documents/{document_id}`).
13. Document deletion (`DELETE /api/v1/documents/{document_id}`).
14. All 39 Phase 1–3 automated unit and relational tests.

---

## 5. Previous Implementation Removed/Replaced
- **Direct PDF Parsing**: Replaced custom `pypdf.PdfReader` iteration with LangChain's official `PyPDFLoader`.
- **Custom Sliding-Window Chunker**: Replaced custom text slicing with LangChain's `RecursiveCharacterTextSplitter`.
- **Empty chroma_id**: In the earlier draft, `chroma_id` was left as `NULL`. In the corrected implementation, `chroma_id` is populated with a deterministic, traceable vector identifier.

---

## 6. LangChain Implementation
- LangChain core `Document` representation is used as the universal internal data structure across the document pipeline.
- Both PDF pages and PPTX slides are converted into `langchain_core.documents.Document` instances with uniform metadata:
  ```python
  Document(page_content="...", metadata={"page": 1, "page_number": 1, "source": "filename.pdf"})
  ```

---

## 7. PyPDFLoader Implementation
- Located in `load_pdf_with_langchain()` within `app/services/document_parser.py`.
- Utilizes `langchain_community.document_loaders.PyPDFLoader(file_path).load()`.
- Extracts each page as a LangChain `Document`.
- Automatically maps 0-indexed `doc.metadata['page']` to 1-indexed integers for human-readable audit and source grounding.

---

## 8. Splitter Implementation
- **Structure-Preserving Recursive Text Splitting**: As clarified by directives, `RecursiveCharacterTextSplitter` is a structure-preserving recursive text splitter (not an embedding-based semantic splitter).
- Splits hierarchically along natural document boundaries:
  ```python
  separators=["\n\n", "\n", " ", ""]
  ```
- Configurable via `settings.CHUNK_SIZE = 1000` and `settings.CHUNK_OVERLAP = 150`.
- Retains source metadata (`page_number`, `source`) across all resulting chunks.

---

## 9. Mistral Embeddings Implementation
- Located in `app/services/embedding_service.py`.
- Implemented via `langchain_mistralai.MistralAIEmbeddings`.
- Model: `mistral-embed` (configurable via `MISTRAL_EMBEDDING_MODEL`).
- API Key: Loaded exclusively from `MISTRAL_API_KEY` environment variable. Never hard-coded, never logged.
- **Dynamic Dimensionality**: Vector dimensionality is handled dynamically from the model response without any hard-coded dimension assertions in production code.
- If credentials are missing, raises `EmbeddingConfigurationError`, which cleanly fails the document processing with a sanitized message.

---

## 10. ChromaDB Implementation
- Located in `app/services/vector_store.py`.
- Uses persistent client: `chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIRECTORY)`.
- Dedicated collection: `settings.CHROMA_COLLECTION_NAME = "statkarmayogi_chunks"`.
- Records store:
  - `ids`: Traceable string identifier (`doc_{document_id}_chunk_{chunk_index}_{content_hash[:16]}`).
  - `embeddings`: Float vector array.
  - `documents`: Chunk text content.
  - `metadatas`: `{"document_id": int, "chunk_index": int, "page_number": int, "content_hash": str, "filename": str}`.

---

## 11. PostgreSQL Traceability
- PostgreSQL `document_chunks` table links every chunk to its ChromaDB vector via `chroma_id`.
- Directional traceability:
  $$\text{PostgreSQL } \texttt{document\_chunks.chroma\_id} \longleftrightarrow \text{ChromaDB Record ID}$$
- Enables ground-truth linking from future generated MCQs (`questions.source_chunk_id`) through `document_chunks` to the exact ChromaDB vector and source page.

---

## 12. chroma_id Behavior
- Pattern: `f"doc_{document_id}_chunk_{chunk_index}_{content_hash[:16]}"`
- Example: `doc_12_chunk_0_a9856d4e2dcffbce`
- Populated immediately after ChromaDB indexing succeeds.
- Never left as `NULL` for successfully processed documents.

---

## 13. Retrieval Implementation
- Located in `VectorStoreService.similarity_search()`.
- Converts search query to vector via `EmbeddingService.embed_query(query)`.
- Executes cosine/distance similarity query on ChromaDB collection with optional `where={"document_id": document_id}`.
- Exposed via authenticated API: `POST /api/v1/documents/search`.

---

## 14. Deletion Synchronization
When `DELETE /api/v1/documents/{document_id}` is executed:
1. Enforces role authorization (uploader or `ADMIN`) and referential integrity against `questions`.
2. Purges vectors from ChromaDB: `VectorStoreService.delete_document_vectors(document.id)`.
3. Deletes PostgreSQL `Document` record (foreign key `CASCADE` removes `document_chunks`).
4. Unlinks physical file from storage.

---

## 15. Idempotency & Failure Compensation Strategy
### Idempotency
- Uses ChromaDB `collection.upsert(...)` with deterministic IDs. Reprocessing the same document does not produce duplicate vectors.
### Failure Compensation (Two-System Consistency)
Because PostgreSQL and ChromaDB do not share a single transaction:
- If ChromaDB vector insertion fails: PostgreSQL transaction rolls back; document status becomes `FAILED`; zero chunks exist in DB.
- If PostgreSQL chunk persistence fails after ChromaDB insertion:
  1. The added ChromaDB vectors are immediately purged via `VectorStoreService.delete_by_ids(inserted_chroma_ids)`.
  2. PostgreSQL transaction rolls back.
  3. A fresh transaction updates `Document.status = FAILED` with a clean error message.
  4. No orphaned ChromaDB vectors or dangling `chroma_id` references remain.

---

## 16. Security
- API keys loaded strictly from environment variables and never logged or exposed.
- Directory traversal patterns (`..`, `/`, `\`) stripped during upload.
- File size enforced during chunked streaming (`HTTP 413 Content Too Large`).
- Internal server file paths and stack traces omitted from public API schemas.

---

## 17. Tests
Full test suite of 63 automated tests:
- `tests/test_auth.py`: 24 tests
- `tests/test_health.py`: 5 tests
- `tests/test_models.py`: 10 tests
- `tests/test_documents.py`: 24 tests

### Results
```powershell
python -m pytest -v
```
```
============================= 63 passed in 4.99s =============================
```
100% pass rate. All tests executed with mock embeddings and isolated temporary ChromaDB storage.

---

## 18. Manual Verification
Executed `scratch/verify_phase_4_rag.py` against live PostgreSQL and ChromaDB:
- [x] Step 1: Trainer registered and authenticated.
- [x] Step 2: Uploaded real PDF.
- [x] Step 3: Verified document status = `PROCESSED`.
- [x] Step 4: Verified 2 `document_chunks` created in PostgreSQL.
- [x] Step 5: Verified `chroma_id` populated (`doc_90_chunk_0_...`).
- [x] Step 6: Verified ChromaDB contains corresponding vectors and metadata.
- [x] Step 7 & 8: Executed semantic similarity search; retrieved relevant chunk.
- [x] Step 9: Source metadata and page numbers verified in search hit.
- [x] Step 10: Deleted document via `DELETE /api/v1/documents/{id}`.
- [x] Step 11: Confirmed PostgreSQL document and chunks removed (0 remaining).
- [x] Step 12: Confirmed ChromaDB vectors removed (0 remaining).
- [x] Step 13: Confirmed physical file unlinked from disk.

---

## 19. Environment Variables Required
```bash
MISTRAL_API_KEY=your_mistral_api_key
MISTRAL_EMBEDDING_MODEL=mistral-embed
CHROMA_PERSIST_DIRECTORY=storage/chroma
CHROMA_COLLECTION_NAME=statkarmayogi_chunks
UPLOAD_DIR=storage/documents
MAX_UPLOAD_SIZE_MB=20
CHUNK_SIZE=1000
CHUNK_OVERLAP=150
```

---

## 20. Limitations
- Legacy binary OLE `.ppt` files are not supported natively by `PyPDFLoader` or `python-pptx`; users must upload modern `.pptx` or `.pdf` formats.
- Live Mistral API calls require a valid `MISTRAL_API_KEY`. In the absence of an API key, the service fails safely with `EmbeddingConfigurationError`.

---

## 21. Any Unresolved Issues
**None**. All requirements and user corrections have been implemented and verified.

---

## 22. Confirmation of MVP Boundaries
- **Strictly No Phase 5+ Functionality**:
  - No Mistral LLM question generation or prompt construction.
  - No MCQ generation or Pydantic question validation.
  - No SME review workflow or approval queue.
  - No officer assessment engine or scoring.
  - No iGOT recommendation algorithms.
