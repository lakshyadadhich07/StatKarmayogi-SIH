import hashlib
import io
import os
import shutil
import tempfile
import uuid
import chromadb
import fpdf
from pptx import Presentation
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token
from app.db.seed import seed_roles
from app.db.session import SessionLocal
from app.main import app
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.enums import DocumentStatus, RoleName
from app.models.role import Role
from app.models.user import User
from app.services.document_chunker import create_chunks_from_documents
from app.services.document_parser import load_document_pages
from app.services.document_service import DocumentService
from app.services.embedding_service import (
    EmbeddingConfigurationError,
    EmbeddingService,
)
from app.services.vector_store import VectorStoreService

client = TestClient(app)


class MockMistralEmbeddings:
    """Deterministic mock embedding generator for tests.
    
    Produces normalized unit vectors without hard-coding dimension in production code.
    """
    def __init__(self, dim: int = 64):
        self.dim = dim

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        h = int(hashlib.sha256(text.strip().encode("utf-8")).hexdigest(), 16)
        vec = [((h >> (i % 60)) & 0xFF) / 255.0 for i in range(self.dim)]
        norm = sum(x * x for x in vec) ** 0.5 or 1.0
        return [round(x / norm, 6) for x in vec]


@pytest.fixture(scope="session", autouse=True)
def isolated_storage():
    """Redirects UPLOAD_DIR to an isolated temporary folder for all tests."""
    temp_dir = tempfile.mkdtemp(prefix="statkarmayogi_test_storage_")
    original_upload_dir = settings.UPLOAD_DIR
    settings.UPLOAD_DIR = temp_dir
    yield temp_dir
    settings.UPLOAD_DIR = original_upload_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="session", autouse=True)
def isolated_chroma():
    """Configures ChromaDB to use an isolated temporary directory during testing."""
    temp_chroma_dir = tempfile.mkdtemp(prefix="statkarmayogi_test_chroma_")
    test_client = chromadb.PersistentClient(path=temp_chroma_dir)
    original_client = VectorStoreService._client
    VectorStoreService.set_client(test_client)
    yield temp_chroma_dir
    VectorStoreService.set_client(original_client)
    shutil.rmtree(temp_chroma_dir, ignore_errors=True)


@pytest.fixture(autouse=True)
def setup_mock_embeddings():
    """Ensures MockMistralEmbeddings is used by default for all automated tests."""
    mock_client = MockMistralEmbeddings(dim=64)
    original = EmbeddingService._instance
    EmbeddingService.set_embeddings_client(mock_client)
    yield
    EmbeddingService.set_embeddings_client(original)


@pytest.fixture(scope="module", autouse=True)
def setup_roles_and_users():
    """Seeds roles and creates test users for TRAINER, ADMIN, SME, OFFICER."""
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
        email = f"{role_name.value.lower()}_{unique_suffix}@mospi.test"
        user = User(
            name=f"Test {role_name.value}",
            email=email,
            password_hash="test_hashed_pwd",
            role_id=role.id,
            department="Testing",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        token = create_access_token(data={"sub": str(user.id), "email": user.email, "role": role_name.value})
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


def generate_pptx_bytes(slides_text: list[str]) -> bytes:
    """Generates an in-memory PPTX with known text on each slide."""
    prs = Presentation()
    for text in slides_text:
        slide = prs.slides.add_slide(prs.slide_layouts[0])
        slide.shapes.title.text = text
    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


# 1. Unauthenticated upload rejected
def test_unauthenticated_upload_rejected():
    pdf_bytes = generate_pdf_bytes(["Test content"])
    response = client.post(
        "/api/v1/documents",
        files={"file": ("sample.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 401


# 2. Authorized user (TRAINER) can upload PDF and gets PROCESSED
def test_authorized_trainer_can_upload_pdf():
    trainer = create_user_with_role(RoleName.TRAINER)
    pdf_bytes = generate_pdf_bytes(["Statistical Methods\nMean, median and mode."])
    response = client.post(
        "/api/v1/documents",
        headers=trainer["headers"],
        files={"file": ("training_stats.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "training_stats.pdf"
    assert data["file_type"] == "PDF"
    assert data["status"] == "PROCESSED"
    assert data["uploaded_by"] == trainer["user_id"]
    assert data["processing_error"] is None


# 3. Authorized user (ADMIN) can upload PPTX
def test_authorized_admin_can_upload_pptx():
    admin = create_user_with_role(RoleName.ADMIN)
    pptx_bytes = generate_pptx_bytes(["Slide 1: Overview", "Slide 2: Data Collection"])
    response = client.post(
        "/api/v1/documents",
        headers=admin["headers"],
        files={"file": ("presentation.pptx", pptx_bytes, "application/vnd.openxmlformats-officedocument.presentationml.presentation")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "presentation.pptx"
    assert data["file_type"] == "PPTX"
    assert data["status"] == "PROCESSED"
    assert data["uploaded_by"] == admin["user_id"]


# 4. Unauthorized roles (OFFICER and SME) cannot upload documents
def test_unauthorized_roles_cannot_upload():
    officer = create_user_with_role(RoleName.OFFICER)
    sme = create_user_with_role(RoleName.SME)
    pdf_bytes = generate_pdf_bytes(["Content"])

    resp_officer = client.post(
        "/api/v1/documents",
        headers=officer["headers"],
        files={"file": ("test.pdf", pdf_bytes, "application/pdf")},
    )
    assert resp_officer.status_code == 403

    resp_sme = client.post(
        "/api/v1/documents",
        headers=sme["headers"],
        files={"file": ("test.pdf", pdf_bytes, "application/pdf")},
    )
    assert resp_sme.status_code == 403


# 5. Unsupported file extension rejected
def test_unsupported_file_extension_rejected():
    trainer = create_user_with_role(RoleName.TRAINER)
    response = client.post(
        "/api/v1/documents",
        headers=trainer["headers"],
        files={"file": ("malicious.exe", b"MZexecutablecontent", "application/octet-stream")},
    )
    assert response.status_code == 400
    assert "Unsupported file extension" in response.json()["detail"]


# 6. Oversized file rejected
def test_oversized_file_rejected(monkeypatch):
    trainer = create_user_with_role(RoleName.TRAINER)
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 1)
    large_bytes = b"0" * (1024 * 1024 + 1024)
    response = client.post(
        "/api/v1/documents",
        headers=trainer["headers"],
        files={"file": ("large_file.pdf", large_bytes, "application/pdf")},
    )
    assert response.status_code == 413
    assert "exceeds maximum allowed size" in response.json()["detail"]


# 7. Filename and path traversal attempts are handled safely
def test_path_traversal_filename_sanitized():
    trainer = create_user_with_role(RoleName.TRAINER)
    pdf_bytes = generate_pdf_bytes(["Safe content here"])
    traversal_name = "../../etc/passwd.pdf"
    response = client.post(
        "/api/v1/documents",
        headers=trainer["headers"],
        files={"file": (traversal_name, pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 201
    data = response.json()
    assert "/" not in data["filename"]
    assert "\\" not in data["filename"]
    assert ".." not in data["filename"]
    assert "passwd.pdf" in data["filename"]


# 8. Document record created in PostgreSQL and file persisted in storage
def test_document_record_and_file_existence():
    trainer = create_user_with_role(RoleName.TRAINER)
    pdf_bytes = generate_pdf_bytes(["Document Existence Verification Text"])
    response = client.post(
        "/api/v1/documents",
        headers=trainer["headers"],
        files={"file": ("exists_test.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 201
    doc_id = response.json()["id"]

    db = SessionLocal()
    try:
        db_doc = db.query(Document).filter(Document.id == doc_id).first()
        assert db_doc is not None
        assert db_doc.filename == "exists_test.pdf"
        assert db_doc.status == DocumentStatus.PROCESSED
        assert os.path.exists(db_doc.file_path)
        assert os.path.isfile(db_doc.file_path)
    finally:
        db.close()


# 9. PPTX slides preserved in chunks and ChromaDB
def test_pptx_slides_preserved_in_chunks_and_chroma():
    trainer = create_user_with_role(RoleName.TRAINER)
    slide_1 = "Slide 1: National Accounts Overview"
    slide_2 = "Slide 2: GDP Computation Methodology"
    pptx_bytes = generate_pptx_bytes([slide_1, slide_2])

    response = client.post(
        "/api/v1/documents",
        headers=trainer["headers"],
        files={"file": ("national_accounts.pptx", pptx_bytes, "application/vnd.openxmlformats-officedocument.presentationml.presentation")},
    )
    assert response.status_code == 201
    doc_id = response.json()["id"]

    db = SessionLocal()
    try:
        chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).order_by(DocumentChunk.chunk_index).all()
        assert len(chunks) == 2
        assert chunks[0].page_number == 1
        assert chunks[1].page_number == 2

        collection = VectorStoreService.get_collection()
        res = collection.get(ids=[c.chroma_id for c in chunks])
        assert len(res["ids"]) == 2
    finally:
        db.close()


# 10. SHA-256 content_hash is deterministic
def test_sha256_content_hash_deterministic():
    trainer = create_user_with_role(RoleName.TRAINER)
    sample_text = "Deterministic SHA-256 content verification text for MoSPI StatKarmayogi."
    expected_hash = hashlib.sha256(sample_text.strip().encode("utf-8")).hexdigest()
    pdf_bytes = generate_pdf_bytes([sample_text])

    response = client.post(
        "/api/v1/documents",
        headers=trainer["headers"],
        files={"file": ("sha_test.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 201
    doc_id = response.json()["id"]

    db = SessionLocal()
    try:
        chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).all()
        assert len(chunks) == 1
        assert chunks[0].content_hash == expected_hash
    finally:
        db.close()


# 11. LangChain PyPDFLoader and RecursiveCharacterTextSplitter verification
def test_langchain_pypdfloader_and_recursive_splitter():
    pdf_bytes = generate_pdf_bytes([
        "Chapter 1: Descriptive Statistics\n\nMean, median, and mode summarize central values.",
        "Chapter 2: Inferential Statistics\n\nHypothesis testing and confidence intervals.",
    ])
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        pdf_path = f.name
        f.write(pdf_bytes)

    try:
        # Verify PyPDFLoader loads pages as LangChain Documents
        docs = load_document_pages(pdf_path, "pdf")
        assert len(docs) == 2
        assert docs[0].metadata["page"] == 1
        assert docs[1].metadata["page"] == 2
        assert "Descriptive Statistics" in docs[0].page_content

        # Verify RecursiveCharacterTextSplitter splits documents
        chunks = create_chunks_from_documents(docs, document_id=101, chunk_size=500, chunk_overlap=50)
        assert len(chunks) == 2
        assert chunks[0]["page_number"] == 1
        assert chunks[1]["page_number"] == 2
        assert chunks[0]["chunk_index"] == 0
        assert chunks[1]["chunk_index"] == 1
        assert chunks[0]["chroma_id"].startswith("doc_101_chunk_0_")
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)


# 9. chroma_id is populated in PostgreSQL document_chunks and matches ChromaDB
def test_chroma_id_populated_and_traceable():
    trainer = create_user_with_role(RoleName.TRAINER)
    pdf_bytes = generate_pdf_bytes(["MoSPI National Sampling Survey Data"])
    response = client.post(
        "/api/v1/documents",
        headers=trainer["headers"],
        files={"file": ("sampling.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 201
    doc_id = response.json()["id"]

    db = SessionLocal()
    try:
        chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).all()
        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.chroma_id is not None
            assert chunk.chroma_id.startswith(f"doc_{doc_id}_chunk_{chunk.chunk_index}_")
            assert chunk.content_hash is not None

        # Verify vectors exist in ChromaDB collection
        collection = VectorStoreService.get_collection()
        chroma_ids = [c.chroma_id for c in chunks]
        results = collection.get(ids=chroma_ids, include=["metadatas", "documents"])
        assert len(results["ids"]) == len(chunks)
        for meta in results["metadatas"]:
            assert meta["document_id"] == doc_id
    finally:
        db.close()


# 10. Semantic retrieval returns expected chunk and metadata
def test_semantic_retrieval_endpoint():
    trainer = create_user_with_role(RoleName.TRAINER)
    content_text = "Gross Value Added (GVA) is defined as output minus intermediate consumption."
    pdf_bytes = generate_pdf_bytes([content_text])
    upload_resp = client.post(
        "/api/v1/documents",
        headers=trainer["headers"],
        files={"file": ("national_gva.pdf", pdf_bytes, "application/pdf")},
    )
    doc_id = upload_resp.json()["id"]

    # Search via POST /api/v1/documents/search
    search_resp = client.post(
        "/api/v1/documents/search",
        headers=trainer["headers"],
        json={"query": "Gross Value Added GVA intermediate consumption", "document_id": doc_id, "top_k": 3},
    )
    assert search_resp.status_code == 200
    results = search_resp.json()
    assert len(results) > 0
    top_hit = results[0]
    assert top_hit["document_id"] == doc_id
    assert "Gross Value Added" in top_hit["content"]
    assert top_hit["chroma_id"].startswith(f"doc_{doc_id}_chunk_")


# 11. Document deletion removes vectors from ChromaDB in addition to PostgreSQL and disk
def test_deletion_removes_chroma_vectors():
    trainer = create_user_with_role(RoleName.TRAINER)
    pdf_bytes = generate_pdf_bytes(["Content to be deleted from ChromaDB"])
    upload_resp = client.post(
        "/api/v1/documents",
        headers=trainer["headers"],
        files={"file": ("to_delete.pdf", pdf_bytes, "application/pdf")},
    )
    doc_id = upload_resp.json()["id"]

    collection = VectorStoreService.get_collection()
    before_check = collection.get(where={"document_id": doc_id})
    assert len(before_check["ids"]) > 0

    del_resp = client.delete(f"/api/v1/documents/{doc_id}", headers=trainer["headers"])
    assert del_resp.status_code == 200

    # ChromaDB vectors must be removed
    after_check = collection.get(where={"document_id": doc_id})
    assert len(after_check["ids"]) == 0

    # PostgreSQL records must be removed
    db = SessionLocal()
    try:
        assert db.query(Document).filter(Document.id == doc_id).first() is None
        assert db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).count() == 0
    finally:
        db.close()


# 12. Failure compensation: If DB persistence fails after Chroma insertion, Chroma vectors are purged
def test_explicit_failure_compensation_purges_chroma():
    trainer = create_user_with_role(RoleName.TRAINER)
    pdf_bytes = generate_pdf_bytes(["Content testing compensation purge"])

    # Temporarily monkeypatch DocumentService to simulate DB failure after Chroma indexing
    orig_add_chunks = VectorStoreService.add_chunks
    captured_chroma_ids = []

    def mock_add_chunks(*args, **kwargs):
        ids = orig_add_chunks(*args, **kwargs)
        captured_chroma_ids.extend(ids)
        return ids

    VectorStoreService.add_chunks = mock_add_chunks

    # Monkeypatch db.add for DocumentChunk to trigger an exception
    orig_add = Session.add

    def fail_on_chunk_add(self, instance):
        if isinstance(instance, DocumentChunk):
            raise RuntimeError("Simulated database failure during chunk persistence")
        return orig_add(self, instance)

    Session.add = fail_on_chunk_add

    try:
        upload_resp = client.post(
            "/api/v1/documents",
            headers=trainer["headers"],
            files={"file": ("fail_compensation.pdf", pdf_bytes, "application/pdf")},
        )
        assert upload_resp.status_code == 201
        data = upload_resp.json()
        assert data["status"] == "FAILED"
        assert "Simulated database failure" in data["processing_error"]

        # Confirm Chroma vectors were purged by compensation!
        collection = VectorStoreService.get_collection()
        results = collection.get(ids=captured_chroma_ids)
        assert len(results["ids"]) == 0
    finally:
        VectorStoreService.add_chunks = orig_add_chunks
        Session.add = orig_add


# 13. Missing Mistral API key fails safely with non-sensitive error
def test_missing_mistral_api_key_fails_safely():
    trainer = create_user_with_role(RoleName.TRAINER)
    # Temporarily unset mock client and set MISTRAL_API_KEY to None
    EmbeddingService.set_embeddings_client(None)
    orig_key = settings.MISTRAL_API_KEY
    settings.MISTRAL_API_KEY = None

    try:
        pdf_bytes = generate_pdf_bytes(["Content with missing key"])
        response = client.post(
            "/api/v1/documents",
            headers=trainer["headers"],
            files={"file": ("missing_key.pdf", pdf_bytes, "application/pdf")},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "FAILED"
        assert "MISTRAL_API_KEY is not configured" in data["processing_error"]

        db = SessionLocal()
        try:
            chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == data["id"]).all()
            assert len(chunks) == 0
        finally:
            db.close()
    finally:
        settings.MISTRAL_API_KEY = orig_key


# 14. Reprocessing idempotency: upsert does not create duplicate ChromaDB vectors
def test_reprocessing_idempotency():
    trainer = create_user_with_role(RoleName.TRAINER)
    pdf_bytes = generate_pdf_bytes(["Idempotency check content"])
    upload_resp = client.post(
        "/api/v1/documents",
        headers=trainer["headers"],
        files={"file": ("idempotent.pdf", pdf_bytes, "application/pdf")},
    )
    doc_id = upload_resp.json()["id"]

    collection = VectorStoreService.get_collection()
    initial_count = len(collection.get(where={"document_id": doc_id})["ids"])

    # Trigger re-indexing of the same chunks directly through VectorStoreService.add_chunks
    db = SessionLocal()
    try:
        db_doc = db.query(Document).filter(Document.id == doc_id).first()
        db_chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).all()
        chunks_data = [
            {"chunk_index": c.chunk_index, "content_hash": c.content_hash, "page_number": c.page_number, "text": "Idempotency check content"}
            for c in db_chunks
        ]
        embeddings = EmbeddingService.embed_documents(["Idempotency check content"] * len(chunks_data))
        VectorStoreService.add_chunks(document_id=doc_id, filename=db_doc.filename, chunks=chunks_data, embeddings=embeddings)

        # Count must remain exactly the same due to upsert on deterministic ID
        recheck_count = len(collection.get(where={"document_id": doc_id})["ids"])
        assert recheck_count == initial_count
    finally:
        db.close()


# 15. Empty document becomes FAILED and creates no chunks or Chroma vectors
def test_empty_document_becomes_failed():
    trainer = create_user_with_role(RoleName.TRAINER)
    pdf = fpdf.FPDF()
    pdf.add_page()
    raw = pdf.output(dest="S")
    empty_pdf_bytes = raw.encode("latin1") if isinstance(raw, str) else raw

    response = client.post(
        "/api/v1/documents",
        headers=trainer["headers"],
        files={"file": ("empty.pdf", empty_pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "FAILED"
    assert "No extractable text" in data["processing_error"]

    db = SessionLocal()
    try:
        chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == data["id"]).all()
        assert len(chunks) == 0
    finally:
        db.close()

    collection = VectorStoreService.get_collection()
    assert len(collection.get(where={"document_id": data["id"]})["ids"]) == 0


# 16. Corrupted file parser failure becomes FAILED
def test_parser_failure_becomes_failed():
    trainer = create_user_with_role(RoleName.TRAINER)
    corrupted_bytes = b"%PDF-corrupted-binary-header-with-invalid-trailer"

    response = client.post(
        "/api/v1/documents",
        headers=trainer["headers"],
        files={"file": ("corrupt.pdf", corrupted_bytes, "application/pdf")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "FAILED"
    assert "Processing error" in data["processing_error"] or "Failed to load" in data["processing_error"]


# 17. Document list endpoint works
def test_document_list_endpoint():
    officer = create_user_with_role(RoleName.OFFICER)
    response = client.get("/api/v1/documents", headers=officer["headers"])
    assert response.status_code == 200
    docs = response.json()
    assert isinstance(docs, list)
    assert len(docs) > 0


# 18. Document detail endpoint returns metadata and chunk count
def test_document_detail_endpoint():
    trainer = create_user_with_role(RoleName.TRAINER)
    pdf_bytes = generate_pdf_bytes(["Detail page 1", "Detail page 2"])
    upload_resp = client.post(
        "/api/v1/documents",
        headers=trainer["headers"],
        files={"file": ("detail_doc.pdf", pdf_bytes, "application/pdf")},
    )
    doc_id = upload_resp.json()["id"]

    detail_resp = client.get(f"/api/v1/documents/{doc_id}", headers=trainer["headers"])
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["id"] == doc_id
    assert detail["chunk_count"] == 2
    assert "file_path" not in detail


# 19. Unauthorized deletion is rejected
def test_unauthorized_deletion_rejected():
    trainer1 = create_user_with_role(RoleName.TRAINER)
    trainer2 = create_user_with_role(RoleName.TRAINER)

    pdf_bytes = generate_pdf_bytes(["Trainer 1 private upload"])
    upload_resp = client.post(
        "/api/v1/documents",
        headers=trainer1["headers"],
        files={"file": ("trainer1_doc.pdf", pdf_bytes, "application/pdf")},
    )
    doc_id = upload_resp.json()["id"]

    resp_trainer2 = client.delete(f"/api/v1/documents/{doc_id}", headers=trainer2["headers"])
    assert resp_trainer2.status_code == 403


# 20. Authorized deletion by ADMIN removes document and ChromaDB vectors
def test_admin_can_delete_any_document():
    trainer = create_user_with_role(RoleName.TRAINER)
    admin = create_user_with_role(RoleName.ADMIN)

    pdf_bytes = generate_pdf_bytes(["Admin deletion test"])
    upload_resp = client.post(
        "/api/v1/documents",
        headers=trainer["headers"],
        files={"file": ("admin_del.pdf", pdf_bytes, "application/pdf")},
    )
    doc_id = upload_resp.json()["id"]

    collection = VectorStoreService.get_collection()
    assert len(collection.get(where={"document_id": doc_id})["ids"]) > 0

    del_resp = client.delete(f"/api/v1/documents/{doc_id}", headers=admin["headers"])
    assert del_resp.status_code == 200

    assert len(collection.get(where={"document_id": doc_id})["ids"]) == 0


# 21. Non-existent document returns 404
def test_nonexistent_document_detail_and_delete_404():
    admin = create_user_with_role(RoleName.ADMIN)
    resp_get = client.get("/api/v1/documents/999999", headers=admin["headers"])
    assert resp_get.status_code == 404

    resp_del = client.delete("/api/v1/documents/999999", headers=admin["headers"])
    assert resp_del.status_code == 404
