import hashlib
import io
import os
import re
import shutil
import tempfile
import uuid
import chromadb
import fpdf
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token
from app.db.seed import seed_roles
from app.db.session import SessionLocal
from app.main import app
from app.models.competency import Competency
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.enums import DocumentStatus, QuestionDifficulty, QuestionStatus, ReviewAction, RoleName
from app.models.question import Question
from app.models.question_review import QuestionReview
from app.models.role import Role
from app.models.user import User
from app.schemas.question import MCQGenerationBatch, MCQGenerationItem
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.services.vector_store import VectorStoreService

client = TestClient(app)


class MockMistralEmbeddings:
    """Deterministic mock embedding generator for tests."""

    def __init__(self, dim: int = 64):
        self.dim = dim

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        h = int(hashlib.sha256(text.strip().encode("utf-8")).hexdigest(), 16)
        vec = [((h >> (i % 60)) & 0xFF) / 255.0 for i in range(self.dim)]
        norm = sum(x * x for x in vec) ** 0.5 or 1.0
        return [round(x / norm, 6) for x in vec]


class MockChatMistralAI:
    """Mock ChatMistralAI supporting with_structured_output for zero-credit testing."""

    def __init__(self, handler=None, default_items=None):
        self.handler = handler
        self.default_items = default_items or []

    def with_structured_output(self, schema):
        parent = self

        class MockRunnable:
            def invoke(self, messages):
                if parent.handler:
                    return parent.handler(messages)
                return MCQGenerationBatch(questions=parent.default_items)

        return MockRunnable()


def default_llm_response_handler(messages):
    """Parses chunk markers from prompt and returns realistic MCQs referencing those chunks."""
    user_prompt = ""
    for m in messages:
        content = getattr(m, "content", "")
        if "=== SOURCE CONTEXT CHUNKS ===" in content:
            user_prompt = content
            break

    chunk_matches = re.findall(r"\[CHUNK ID: (\d+), PAGE: (\d+)\]", user_prompt)
    questions = []
    for i, (cid_str, page_str) in enumerate(chunk_matches):
        cid = int(cid_str)
        pno = int(page_str)
        questions.append(
            MCQGenerationItem(
                question_text=f"What is the primary statistical definition described in source chunk {cid}?",
                option_a=f"Correct definition established on page {pno} for chunk {cid}",
                option_b=f"Plausible distractor 1 regarding survey methodologies for chunk {cid}",
                option_c=f"Plausible distractor 2 concerning classification codes for chunk {cid}",
                option_d=f"Plausible distractor 3 regarding data dissemination for chunk {cid}",
                correct_option="A",
                difficulty=QuestionDifficulty.MEDIUM,
                explanation=f"Based on source chunk {cid} on page {pno}, option A is directly verified by the text.",
                source_chunk_id=cid,
            )
        )
    return MCQGenerationBatch(questions=questions)


@pytest.fixture(scope="session", autouse=True)
def isolated_storage():
    """Redirects UPLOAD_DIR to an isolated temporary folder for all tests."""
    temp_dir = tempfile.mkdtemp(prefix="statkarmayogi_test_storage_q_")
    original_upload_dir = settings.UPLOAD_DIR
    settings.UPLOAD_DIR = temp_dir
    yield temp_dir
    settings.UPLOAD_DIR = original_upload_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="session", autouse=True)
def isolated_chroma():
    """Configures ChromaDB to use an isolated temporary directory during testing."""
    temp_chroma_dir = tempfile.mkdtemp(prefix="statkarmayogi_test_chroma_q_")
    test_client = chromadb.PersistentClient(path=temp_chroma_dir)
    original_client = VectorStoreService._client
    VectorStoreService.set_client(test_client)
    yield temp_chroma_dir
    VectorStoreService.set_client(original_client)
    shutil.rmtree(temp_chroma_dir, ignore_errors=True)


@pytest.fixture(autouse=True)
def setup_mock_services():
    """Ensures MockMistralEmbeddings and MockChatMistralAI are used by default."""
    mock_emb = MockMistralEmbeddings(dim=64)
    orig_emb = EmbeddingService._instance
    EmbeddingService.set_embeddings_client(mock_emb)

    mock_llm = MockChatMistralAI(handler=default_llm_response_handler)
    orig_llm = LLMService._instance
    LLMService.set_llm_client(mock_llm)

    yield

    EmbeddingService.set_embeddings_client(orig_emb)
    LLMService.set_llm_client(orig_llm)


@pytest.fixture(scope="module", autouse=True)
def setup_roles_and_users():
    """Seeds roles."""
    db = SessionLocal()
    try:
        seed_roles(db)
    finally:
        db.close()


def create_user_with_role(role_name: RoleName) -> dict:
    """Helper to create or fetch a user with a specific role and return auth headers."""
    db: Session = SessionLocal()
    try:
        role = db.query(Role).filter(Role.name == role_name.value).first()
        assert role is not None
        unique_suffix = uuid.uuid4().hex[:8]
        email = f"user_{role_name.value.lower()}_{unique_suffix}@mospi.test"
        user = User(
            name=f"Test {role_name.value}",
            email=email,
            password_hash="test_hashed_pwd",
            role_id=role.id,
            department="Statistics",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        token = create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": role_name.value}
        )
        return {
            "user_id": user.id,
            "email": user.email,
            "role": role_name.value,
            "token": token,
            "headers": {"Authorization": f"Bearer {token}"},
        }
    finally:
        db.close()


def generate_pdf_bytes(pages_text: list[str]) -> bytes:
    """Generates an in-memory PDF with known text on each page."""
    pdf = fpdf.FPDF()
    for text in pages_text:
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, txt=text)
    raw = pdf.output(dest="S")
    return raw.encode("latin1") if isinstance(raw, str) else raw


def upload_processed_document(trainer_headers: dict, filename: str = "national_accounts.pdf") -> int:
    """Helper to upload a test document and verify it is PROCESSED."""
    pdf_bytes = generate_pdf_bytes([
        "Chapter 1: Gross Domestic Product (GDP) measures total economic output at market prices.",
        "Chapter 2: Consumer Price Index (CPI) measures changes in price level of consumer goods basket.",
    ])
    resp = client.post(
        "/api/v1/documents",
        headers=trainer_headers,
        files={"file": (filename, pdf_bytes, "application/pdf")},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "PROCESSED"
    return data["id"]


# 1. Unauthenticated generation request rejected
def test_unauthenticated_generate_rejected():
    resp = client.post("/api/v1/questions/generate", json={"document_id": 1, "num_questions": 3})
    assert resp.status_code == 401


# 2. OFFICER cannot generate questions (403 Forbidden)
def test_officer_cannot_generate_questions():
    officer = create_user_with_role(RoleName.OFFICER)
    resp = client.post(
        "/api/v1/questions/generate",
        headers=officer["headers"],
        json={"document_id": 1, "num_questions": 3},
    )
    assert resp.status_code == 403


# 3. SME cannot generate questions (403 Forbidden)
def test_sme_cannot_generate_questions():
    sme = create_user_with_role(RoleName.SME)
    resp = client.post(
        "/api/v1/questions/generate",
        headers=sme["headers"],
        json={"document_id": 1, "num_questions": 3},
    )
    assert resp.status_code == 403


# 4. TRAINER can generate MCQs for processed document
def test_trainer_can_generate_mcqs_for_processed_document():
    trainer = create_user_with_role(RoleName.TRAINER)
    doc_id = upload_processed_document(trainer["headers"], "sampling_guide.pdf")

    payload = {
        "document_id": doc_id,
        "num_questions": 2,
        "difficulty": "MEDIUM",
    }
    resp = client.post("/api/v1/questions/generate", headers=trainer["headers"], json=payload)
    assert resp.status_code == 201
    questions = resp.json()
    assert len(questions) == 2

    for q in questions:
        assert q["document_id"] == doc_id
        assert q["status"] == QuestionStatus.PENDING_REVIEW.value
        assert q["created_by"] == trainer["user_id"]
        assert q["question_text"].endswith("?")
        assert q["correct_option"] in {"A", "B", "C", "D"}
        assert len({q["option_a"], q["option_b"], q["option_c"], q["option_d"]}) == 4
        assert q["source_chunk_id"] is not None
        assert q["source_page"] is not None
        assert q["explanation"] is not None

    # Check atomic update of generation_count
    db = SessionLocal()
    try:
        db_doc = db.query(Document).filter(Document.id == doc_id).first()
        assert db_doc.generation_count == 2
    finally:
        db.close()


# 5. ADMIN can generate MCQs
def test_admin_can_generate_mcqs():
    trainer = create_user_with_role(RoleName.TRAINER)
    admin = create_user_with_role(RoleName.ADMIN)
    doc_id = upload_processed_document(trainer["headers"], "cpi_methods.pdf")

    resp = client.post(
        "/api/v1/questions/generate",
        headers=admin["headers"],
        json={"document_id": doc_id, "num_questions": 1},
    )
    assert resp.status_code == 201
    assert len(resp.json()) == 1


# 6. Generate for unprocessed / failed document is rejected
def test_generate_for_unprocessed_document_rejected():
    trainer = create_user_with_role(RoleName.TRAINER)
    # Create a document in UPLOADED or FAILED status
    db = SessionLocal()
    try:
        doc = Document(
            uploaded_by=trainer["user_id"],
            filename="failed_doc.pdf",
            file_type="PDF",
            file_path="storage/documents/failed_doc.pdf",
            status=DocumentStatus.FAILED,
            processing_error="Corrupted PDF trailer",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        failed_doc_id = doc.id
    finally:
        db.close()

    resp = client.post(
        "/api/v1/questions/generate",
        headers=trainer["headers"],
        json={"document_id": failed_doc_id, "num_questions": 2},
    )
    assert resp.status_code == 400
    assert "MCQs can only be generated from PROCESSED documents" in resp.json()["detail"]


# 7. Generate for nonexistent document returns 404
def test_generate_for_nonexistent_document_rejected():
    trainer = create_user_with_role(RoleName.TRAINER)
    resp = client.post(
        "/api/v1/questions/generate",
        headers=trainer["headers"],
        json={"document_id": 999999, "num_questions": 2},
    )
    assert resp.status_code == 404
    assert "was not found" in resp.json()["detail"]


# 8. Competency constraint loaded and linked to generated questions
def test_competency_constraint_loaded_and_used():
    trainer = create_user_with_role(RoleName.TRAINER)
    doc_id = upload_processed_document(trainer["headers"], "national_statistical_survey.pdf")

    # Create active competency
    db = SessionLocal()
    try:
        unique_code = f"COMP_{uuid.uuid4().hex[:6].upper()}"
        comp = Competency(
            code=unique_code,
            name="Sample Survey Design",
            description="Methodologies for designing stratified multi-stage random sampling.",
            category="Domain Specific",
            is_active=True,
        )
        db.add(comp)
        db.commit()
        db.refresh(comp)
        comp_id = comp.id
    finally:
        db.close()

    resp = client.post(
        "/api/v1/questions/generate",
        headers=trainer["headers"],
        json={"document_id": doc_id, "num_questions": 2, "competency_id": comp_id},
    )
    assert resp.status_code == 201
    questions = resp.json()
    assert len(questions) > 0
    for q in questions:
        assert q["competency_id"] == comp_id


# 9. Nonexistent or inactive competency rejected
def test_nonexistent_and_inactive_competency_rejected():
    trainer = create_user_with_role(RoleName.TRAINER)
    doc_id = upload_processed_document(trainer["headers"], "survey_testing.pdf")

    # 404 for nonexistent competency
    resp_404 = client.post(
        "/api/v1/questions/generate",
        headers=trainer["headers"],
        json={"document_id": doc_id, "num_questions": 2, "competency_id": 888888},
    )
    assert resp_404.status_code == 404

    # 400 for inactive competency
    db = SessionLocal()
    try:
        unique_code = f"INACT_{uuid.uuid4().hex[:6].upper()}"
        inactive_comp = Competency(
            code=unique_code,
            name="Retired Standards",
            description="Old 1990 standards.",
            is_active=False,
        )
        db.add(inactive_comp)
        db.commit()
        db.refresh(inactive_comp)
        inact_id = inactive_comp.id
    finally:
        db.close()

    resp_400 = client.post(
        "/api/v1/questions/generate",
        headers=trainer["headers"],
        json={"document_id": doc_id, "num_questions": 2, "competency_id": inact_id},
    )
    assert resp_400.status_code == 400
    assert "is inactive" in resp_400.json()["detail"]


# 10. Explicit source chunk attribution validated (no post-hoc assignment)
def test_explicit_source_chunk_attribution_validated():
    trainer = create_user_with_role(RoleName.TRAINER)
    doc_id = upload_processed_document(trainer["headers"], "attribution_doc.pdf")

    resp = client.post(
        "/api/v1/questions/generate",
        headers=trainer["headers"],
        json={"document_id": doc_id, "num_questions": 2},
    )
    assert resp.status_code == 201
    questions = resp.json()

    db = SessionLocal()
    try:
        valid_chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).all()
        valid_chunk_map = {c.id: c.page_number for c in valid_chunks}

        for q in questions:
            assert q["source_chunk_id"] in valid_chunk_map
            assert q["source_page"] == valid_chunk_map[q["source_chunk_id"]]
    finally:
        db.close()


# 11. Invalid source_chunk_id rejected before persistence
def test_invalid_source_chunk_id_rejected_before_persistence():
    trainer = create_user_with_role(RoleName.TRAINER)
    doc_id = upload_processed_document(trainer["headers"], "hallucinated_chunk.pdf")

    # Mock LLM returns a hallucinated chunk ID not in the retrieved context
    def hallucinating_handler(messages):
        return MCQGenerationBatch(
            questions=[
                MCQGenerationItem(
                    question_text="Hallucinated chunk question?",
                    option_a="A",
                    option_b="B",
                    option_c="C",
                    option_d="D",
                    correct_option="A",
                    difficulty=QuestionDifficulty.EASY,
                    explanation="Hallucination test.",
                    source_chunk_id=999999,  # Invalid chunk ID!
                )
            ]
        )

    LLMService.set_llm_client(MockChatMistralAI(handler=hallucinating_handler))

    resp = client.post(
        "/api/v1/questions/generate",
        headers=trainer["headers"],
        json={"document_id": doc_id, "num_questions": 1},
    )
    # Since all questions failed source chunk attribution, HTTP 502 Bad Gateway is returned
    assert resp.status_code == 502
    assert "source chunk attribution checks" in resp.json()["detail"]


# 12. Duplicate question_text within batch is deduplicated
def test_duplicate_question_text_within_batch_deduplicated():
    trainer = create_user_with_role(RoleName.TRAINER)
    doc_id = upload_processed_document(trainer["headers"], "dedup_test.pdf")

    db = SessionLocal()
    try:
        first_chunk = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).first()
        cid = first_chunk.id
    finally:
        db.close()

    # Mock returns two questions with identical question_text
    def duplicate_handler(messages):
        return MCQGenerationBatch(
            questions=[
                MCQGenerationItem(
                    question_text="What is the formula for calculating CPI?",
                    option_a="Laspeyres index formula",
                    option_b="Paasche index formula",
                    option_c="Fisher ideal index",
                    option_d="Simple unweighted average",
                    correct_option="A",
                    difficulty=QuestionDifficulty.MEDIUM,
                    explanation="CPI in India utilizes the modified Laspeyres formula.",
                    source_chunk_id=cid,
                ),
                MCQGenerationItem(
                    question_text="what is the formula for calculating cpi?",  # Case-insensitive duplicate
                    option_a="Option 1",
                    option_b="Option 2",
                    option_c="Option 3",
                    option_d="Option 4",
                    correct_option="B",
                    difficulty=QuestionDifficulty.MEDIUM,
                    explanation="Duplicate explanation.",
                    source_chunk_id=cid,
                ),
            ]
        )

    LLMService.set_llm_client(MockChatMistralAI(handler=duplicate_handler))

    resp = client.post(
        "/api/v1/questions/generate",
        headers=trainer["headers"],
        json={"document_id": doc_id, "num_questions": 2},
    )
    assert resp.status_code == 201
    questions = resp.json()
    # Duplicate was filtered, only 1 question persisted!
    assert len(questions) == 1
    assert "formula for calculating CPI" in questions[0]["question_text"]


# 13. Structural validation filters questions with non-distinct options or bad keys
def test_structural_validation_filters_invalid_items():
    trainer = create_user_with_role(RoleName.TRAINER)
    doc_id = upload_processed_document(trainer["headers"], "structure_test.pdf")

    db = SessionLocal()
    try:
        first_chunk = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).first()
        cid = first_chunk.id
    finally:
        db.close()

    def invalid_items_handler(messages):
        return MCQGenerationBatch(
            questions=[
                # Duplicate options (only 3 unique choices)
                MCQGenerationItem(
                    question_text="Question with non-distinct options?",
                    option_a="Same Choice",
                    option_b="Same Choice",
                    option_c="Option C",
                    option_d="Option D",
                    correct_option="A",
                    difficulty=QuestionDifficulty.EASY,
                    explanation="Non distinct choices.",
                    source_chunk_id=cid,
                ),
                # Valid item
                MCQGenerationItem(
                    question_text="What is a valid question?",
                    option_a="Alpha",
                    option_b="Beta",
                    option_c="Gamma",
                    option_d="Delta",
                    correct_option="C",
                    difficulty=QuestionDifficulty.EASY,
                    explanation="Valid item explanation.",
                    source_chunk_id=cid,
                ),
            ]
        )

    LLMService.set_llm_client(MockChatMistralAI(handler=invalid_items_handler))

    resp = client.post(
        "/api/v1/questions/generate",
        headers=trainer["headers"],
        json={"document_id": doc_id, "num_questions": 2},
    )
    assert resp.status_code == 201
    questions = resp.json()
    assert len(questions) == 1
    assert questions[0]["question_text"] == "What is a valid question?"


# 14. Atomic single transaction: questions persisted & generation_count incremented together
def test_atomic_persistence_and_generation_count_increment():
    trainer = create_user_with_role(RoleName.TRAINER)
    doc_id = upload_processed_document(trainer["headers"], "atomic_test.pdf")

    resp1 = client.post(
        "/api/v1/questions/generate",
        headers=trainer["headers"],
        json={"document_id": doc_id, "num_questions": 1},
    )
    assert resp1.status_code == 201

    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        assert doc.generation_count == 1
    finally:
        db.close()

    resp2 = client.post(
        "/api/v1/questions/generate",
        headers=trainer["headers"],
        json={"document_id": doc_id, "num_questions": 1},
    )
    assert resp2.status_code == 201

    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        assert doc.generation_count == 2
    finally:
        db.close()


# 15. List questions endpoint filtering and pagination
def test_list_questions_endpoint_and_filters():
    trainer = create_user_with_role(RoleName.TRAINER)
    sme = create_user_with_role(RoleName.SME)
    admin = create_user_with_role(RoleName.ADMIN)
    doc_id = upload_processed_document(trainer["headers"], "listing_test.pdf")

    gen_resp = client.post(
        "/api/v1/questions/generate",
        headers=trainer["headers"],
        json={"document_id": doc_id, "num_questions": 2},
    )
    assert gen_resp.status_code == 201

    # Accessible by TRAINER, SME, and ADMIN
    for role_user in [trainer, sme, admin]:
        resp = client.get(f"/api/v1/questions?document_id={doc_id}", headers=role_user["headers"])
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 2
        assert len(data["items"]) >= 2
        for item in data["items"]:
            assert item["document_id"] == doc_id
            assert item["status"] == QuestionStatus.PENDING_REVIEW.value

    # Filter by status
    resp_pending = client.get(
        f"/api/v1/questions?document_id={doc_id}&status=PENDING_REVIEW",
        headers=trainer["headers"],
    )
    assert resp_pending.status_code == 200
    assert resp_pending.json()["total"] >= 2


# 16. OFFICER cannot list questions (role-based security)
def test_officer_cannot_list_or_view_questions():
    trainer = create_user_with_role(RoleName.TRAINER)
    officer = create_user_with_role(RoleName.OFFICER)
    doc_id = upload_processed_document(trainer["headers"], "officer_rbac.pdf")

    gen_resp = client.post(
        "/api/v1/questions/generate",
        headers=trainer["headers"],
        json={"document_id": doc_id, "num_questions": 1},
    )
    assert gen_resp.status_code == 201
    q_id = gen_resp.json()[0]["id"]

    # Listing forbidden
    resp_list = client.get("/api/v1/questions", headers=officer["headers"])
    assert resp_list.status_code == 403

    # Detail forbidden
    resp_detail = client.get(f"/api/v1/questions/{q_id}", headers=officer["headers"])
    assert resp_detail.status_code == 403


# 17. Question detail retrieval
def test_get_question_by_id_endpoint():
    trainer = create_user_with_role(RoleName.TRAINER)
    doc_id = upload_processed_document(trainer["headers"], "detail_test.pdf")

    gen_resp = client.post(
        "/api/v1/questions/generate",
        headers=trainer["headers"],
        json={"document_id": doc_id, "num_questions": 1},
    )
    assert gen_resp.status_code == 201
    q_id = gen_resp.json()[0]["id"]

    resp = client.get(f"/api/v1/questions/{q_id}", headers=trainer["headers"])
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["id"] == q_id
    assert detail["status"] == QuestionStatus.PENDING_REVIEW.value
    assert detail["difficulty"] == QuestionDifficulty.MEDIUM.value

    # 404 for invalid question ID
    resp_404 = client.get("/api/v1/questions/999999", headers=trainer["headers"])
    assert resp_404.status_code == 404


# 18. Missing Mistral API key fails safely
def test_missing_mistral_api_key_fails_safely():
    trainer = create_user_with_role(RoleName.TRAINER)
    doc_id = upload_processed_document(trainer["headers"], "apikey_test.pdf")

    # Unset mock LLM client and clear MISTRAL_API_KEY
    LLMService.set_llm_client(None)
    orig_key = settings.MISTRAL_API_KEY
    settings.MISTRAL_API_KEY = None

    try:
        resp = client.post(
            "/api/v1/questions/generate",
            headers=trainer["headers"],
            json={"document_id": doc_id, "num_questions": 1},
        )
        assert resp.status_code == 500
        assert "MISTRAL_API_KEY is not configured" in resp.json()["detail"]
    finally:
        settings.MISTRAL_API_KEY = orig_key


# ==========================================
# PHASE 6: SME QUESTION REVIEW TESTS
# ==========================================

# 19. Unauthenticated review rejected (401)
def test_unauthenticated_review_rejected():
    resp = client.post("/api/v1/questions/1/review", json={"action": "APPROVE", "comment": "Test"})
    assert resp.status_code == 401


# 20. TRAINER cannot review question (403 Forbidden)
def test_trainer_cannot_review_question():
    trainer = create_user_with_role(RoleName.TRAINER)
    doc_id = upload_processed_document(trainer["headers"], "trainer_cant_rev.pdf")
    gen_resp = client.post(
        "/api/v1/questions/generate",
        headers=trainer["headers"],
        json={"document_id": doc_id, "num_questions": 1},
    )
    assert gen_resp.status_code == 201
    q_id = gen_resp.json()[0]["id"]

    resp = client.post(
        f"/api/v1/questions/{q_id}/review",
        headers=trainer["headers"],
        json={"action": "APPROVE", "comment": "Trainer attempting review"},
    )
    assert resp.status_code == 403


# 21. OFFICER cannot review question (403 Forbidden)
def test_officer_cannot_review_question():
    trainer = create_user_with_role(RoleName.TRAINER)
    officer = create_user_with_role(RoleName.OFFICER)
    doc_id = upload_processed_document(trainer["headers"], "officer_cant_rev.pdf")
    gen_resp = client.post(
        "/api/v1/questions/generate",
        headers=trainer["headers"],
        json={"document_id": doc_id, "num_questions": 1},
    )
    assert gen_resp.status_code == 201
    q_id = gen_resp.json()[0]["id"]

    resp = client.post(
        f"/api/v1/questions/{q_id}/review",
        headers=officer["headers"],
        json={"action": "APPROVE", "comment": "Officer attempting review"},
    )
    assert resp.status_code == 403


# 22. SME can approve pending question (HTTP 200, status=APPROVED, review audit record)
def test_sme_can_approve_pending_question():
    trainer = create_user_with_role(RoleName.TRAINER)
    sme = create_user_with_role(RoleName.SME)
    doc_id = upload_processed_document(trainer["headers"], "sme_approval.pdf")
    gen_resp = client.post(
        "/api/v1/questions/generate",
        headers=trainer["headers"],
        json={"document_id": doc_id, "num_questions": 1},
    )
    assert gen_resp.status_code == 201
    q_id = gen_resp.json()[0]["id"]

    review_payload = {
        "action": "APPROVE",
        "comment": "Question is factually grounded and methodologically sound.",
    }
    rev_resp = client.post(
        f"/api/v1/questions/{q_id}/review",
        headers=sme["headers"],
        json=review_payload,
    )
    assert rev_resp.status_code == 200
    data = rev_resp.json()
    assert data["question_id"] == q_id
    assert data["reviewer_id"] == sme["user_id"]
    assert data["action"] == "APPROVE"
    assert data["comment"] == "Question is factually grounded and methodologically sound."
    assert data["question_status"] == QuestionStatus.APPROVED.value
    assert data["question"]["status"] == QuestionStatus.APPROVED.value

    # Verify directly in database
    db = SessionLocal()
    try:
        q = db.query(Question).filter(Question.id == q_id).first()
        assert q.status == QuestionStatus.APPROVED

        rev = db.query(QuestionReview).filter(QuestionReview.question_id == q_id).first()
        assert rev is not None
        assert rev.action == ReviewAction.APPROVE
        assert rev.reviewer_id == sme["user_id"]
        assert rev.comment == "Question is factually grounded and methodologically sound."
        assert rev.created_at is not None
    finally:
        db.close()


# 23. SME can reject pending question (HTTP 200, status=REJECTED, rejection comment persisted)
def test_sme_can_reject_pending_question():
    trainer = create_user_with_role(RoleName.TRAINER)
    sme = create_user_with_role(RoleName.SME)
    doc_id = upload_processed_document(trainer["headers"], "sme_rejection.pdf")
    gen_resp = client.post(
        "/api/v1/questions/generate",
        headers=trainer["headers"],
        json={"document_id": doc_id, "num_questions": 1},
    )
    assert gen_resp.status_code == 201
    q_id = gen_resp.json()[0]["id"]

    review_payload = {
        "action": "REJECT",
        "comment": "Option B and C are too similar; needs revision.",
    }
    rev_resp = client.post(
        f"/api/v1/questions/{q_id}/review",
        headers=sme["headers"],
        json=review_payload,
    )
    assert rev_resp.status_code == 200
    data = rev_resp.json()
    assert data["action"] == "REJECT"
    assert data["question_status"] == QuestionStatus.REJECTED.value

    # Verify directly in database
    db = SessionLocal()
    try:
        q = db.query(Question).filter(Question.id == q_id).first()
        assert q.status == QuestionStatus.REJECTED

        rev = db.query(QuestionReview).filter(QuestionReview.question_id == q_id).first()
        assert rev is not None
        assert rev.action == ReviewAction.REJECT
        assert rev.comment == "Option B and C are too similar; needs revision."
    finally:
        db.close()


# 24. ADMIN can review question (approves or rejects)
def test_admin_can_review_question():
    trainer = create_user_with_role(RoleName.TRAINER)
    admin = create_user_with_role(RoleName.ADMIN)
    doc_id = upload_processed_document(trainer["headers"], "admin_review.pdf")
    gen_resp = client.post(
        "/api/v1/questions/generate",
        headers=trainer["headers"],
        json={"document_id": doc_id, "num_questions": 1},
    )
    assert gen_resp.status_code == 201
    q_id = gen_resp.json()[0]["id"]

    rev_resp = client.post(
        f"/api/v1/questions/{q_id}/review",
        headers=admin["headers"],
        json={"action": "APPROVE", "comment": "Admin override approval"},
    )
    assert rev_resp.status_code == 200
    assert rev_resp.json()["action"] == "APPROVE"
    assert rev_resp.json()["question_status"] == QuestionStatus.APPROVED.value


# 25. Review nonexistent question returns 404
def test_review_nonexistent_question():
    sme = create_user_with_role(RoleName.SME)
    resp = client.post(
        "/api/v1/questions/999999/review",
        headers=sme["headers"],
        json={"action": "APPROVE", "comment": "Nonexistent question review"},
    )
    assert resp.status_code == 404
    assert "was not found" in resp.json()["detail"]


# 26. Cannot review already approved question (HTTP 400 Bad Request)
def test_cannot_review_already_approved_question():
    trainer = create_user_with_role(RoleName.TRAINER)
    sme = create_user_with_role(RoleName.SME)
    doc_id = upload_processed_document(trainer["headers"], "double_appr.pdf")
    gen_resp = client.post(
        "/api/v1/questions/generate",
        headers=trainer["headers"],
        json={"document_id": doc_id, "num_questions": 1},
    )
    q_id = gen_resp.json()[0]["id"]

    # First review: approve
    r1 = client.post(
        f"/api/v1/questions/{q_id}/review",
        headers=sme["headers"],
        json={"action": "APPROVE", "comment": "First approval"},
    )
    assert r1.status_code == 200

    # Second review attempt: must fail
    r2 = client.post(
        f"/api/v1/questions/{q_id}/review",
        headers=sme["headers"],
        json={"action": "APPROVE", "comment": "Second approval attempt"},
    )
    assert r2.status_code == 400
    assert "has status 'APPROVED' and cannot be reviewed" in r2.json()["detail"]


# 27. Cannot review already rejected question (HTTP 400 Bad Request)
def test_cannot_review_already_rejected_question():
    trainer = create_user_with_role(RoleName.TRAINER)
    sme = create_user_with_role(RoleName.SME)
    doc_id = upload_processed_document(trainer["headers"], "double_rej.pdf")
    gen_resp = client.post(
        "/api/v1/questions/generate",
        headers=trainer["headers"],
        json={"document_id": doc_id, "num_questions": 1},
    )
    q_id = gen_resp.json()[0]["id"]

    # First review: reject
    r1 = client.post(
        f"/api/v1/questions/{q_id}/review",
        headers=sme["headers"],
        json={"action": "REJECT", "comment": "First rejection"},
    )
    assert r1.status_code == 200

    # Second review attempt: must fail
    r2 = client.post(
        f"/api/v1/questions/{q_id}/review",
        headers=sme["headers"],
        json={"action": "APPROVE", "comment": "Approval attempt on rejected question"},
    )
    assert r2.status_code == 400
    assert "has status 'REJECTED' and cannot be reviewed" in r2.json()["detail"]


# 28. Review record audit trail verification
def test_review_record_contains_reviewer_and_timestamp():
    trainer = create_user_with_role(RoleName.TRAINER)
    sme = create_user_with_role(RoleName.SME)
    doc_id = upload_processed_document(trainer["headers"], "audit_trail.pdf")
    gen_resp = client.post(
        "/api/v1/questions/generate",
        headers=trainer["headers"],
        json={"document_id": doc_id, "num_questions": 1},
    )
    q_id = gen_resp.json()[0]["id"]

    resp = client.post(
        f"/api/v1/questions/{q_id}/review",
        headers=sme["headers"],
        json={"action": "APPROVE", "comment": "Official MoSPI review audit note"},
    )
    assert resp.status_code == 200
    rev_id = resp.json()["id"]

    db = SessionLocal()
    try:
        rev_record = db.query(QuestionReview).filter(QuestionReview.id == rev_id).first()
        assert rev_record is not None
        assert rev_record.question_id == q_id
        assert rev_record.reviewer_id == sme["user_id"]
        assert rev_record.action == ReviewAction.APPROVE
        assert rev_record.comment == "Official MoSPI review audit note"
        assert rev_record.created_at is not None
    finally:
        db.close()


# 29. Atomic transaction rollback on review failure
def test_review_atomic_rollback_on_failure(monkeypatch):
    trainer = create_user_with_role(RoleName.TRAINER)
    sme = create_user_with_role(RoleName.SME)
    doc_id = upload_processed_document(trainer["headers"], "atomic_fail.pdf")
    gen_resp = client.post(
        "/api/v1/questions/generate",
        headers=trainer["headers"],
        json={"document_id": doc_id, "num_questions": 1},
    )
    q_id = gen_resp.json()[0]["id"]

    # Monkeypatch db.add to simulate failure when adding QuestionReview
    orig_add = Session.add

    def fail_on_review_add(self, instance):
        if isinstance(instance, QuestionReview):
            raise RuntimeError("Simulated failure during review audit commit")
        return orig_add(self, instance)

    monkeypatch.setattr(Session, "add", fail_on_review_add)

    resp = client.post(
        f"/api/v1/questions/{q_id}/review",
        headers=sme["headers"],
        json={"action": "APPROVE", "comment": "Failing review test"},
    )
    assert resp.status_code == 500
    assert "Failed to record question review" in resp.json()["detail"]

    # Verify question status was rolled back and remains PENDING_REVIEW
    db = SessionLocal()
    try:
        q = db.query(Question).filter(Question.id == q_id).first()
        assert q.status == QuestionStatus.PENDING_REVIEW
        rev_count = db.query(QuestionReview).filter(QuestionReview.question_id == q_id).count()
        assert rev_count == 0
    finally:
        db.close()
