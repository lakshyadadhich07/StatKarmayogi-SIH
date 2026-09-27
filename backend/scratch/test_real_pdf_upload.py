"""End-to-End Real PDF Upload and Ingestion Verification Script.

Tests the full ingestion pipeline using real Mistral AI Embeddings (1024-dim):
1. Ingests a real multi-page PDF with MoSPI statistical content.
2. Extracts pages with LangChain PyPDFLoader.
3. Splits into deterministic chunks with RecursiveCharacterTextSplitter.
4. Generates real 1024-dimensional Mistral embeddings via live API.
5. Upserts 1024-dim vectors into ChromaDB with deterministic IDs.
6. Persists Document and DocumentChunk records into PostgreSQL.
7. Verifies end-to-end traceability and 1024-dimensional vector storage.
"""
import sys
import os
import io
import uuid
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

import fpdf
from fastapi import UploadFile
from app.core.config import settings
from app.db.session import SessionLocal
from app.db.seed import seed_roles
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.enums import DocumentStatus, RoleName
from app.models.role import Role
from app.models.user import User
from app.services.document_service import DocumentService
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStoreService


def generate_test_pdf_stream() -> io.BytesIO:
    """Creates a realistic 2-page PDF in memory with MoSPI statistical text."""
    pdf = fpdf.FPDF()
    
    # Page 1
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "MoSPI National Sample Survey (NSS) Guidelines", ln=True)
    pdf.set_font("Arial", size=11)
    pdf.multi_cell(
        0, 8,
        "Chapter 1: Multi-Stage Stratified Sampling.\n"
        "The National Sample Survey employs a stratified multi-stage design.\n"
        "The first stage units (FSU) are Census villages in rural areas and\n"
        "Urban Frame Survey (UFS) blocks in urban areas.\n"
        "The ultimate stage units (USU) are households in both sectors.\n"
        "Stratification is carried out by district boundaries and population size."
    )
    
    # Page 2
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Chapter 2: Sampling Variance and Estimation", ln=True)
    pdf.set_font("Arial", size=11)
    pdf.multi_cell(
        0, 8,
        "Ratio method of estimation is adopted for estimating population aggregates.\n"
        "Sub-sample estimates are computed independently to yield unbiased variance estimators.\n"
        "Standard errors are published alongside point estimates to ensure quality control."
    )

    buf = io.BytesIO()
    raw = pdf.output(dest="S")
    buf.write(raw.encode("latin1") if isinstance(raw, str) else raw)
    buf.seek(0)
    return buf


def run_real_pdf_upload_test() -> bool:
    print("=" * 80)
    print("REAL PDF UPLOAD & 1024-DIM MISTRAL INGESTION TEST")
    print("=" * 80)

    # 1. Check API Key
    if not settings.MISTRAL_API_KEY or not settings.MISTRAL_API_KEY.strip():
        print("\n[FAILED] MISTRAL_API_KEY is not configured in .env.")
        return False
    if settings.MISTRAL_API_KEY.strip() == "your-mistral-api-key-here":
        print("\n[FAILED] MISTRAL_API_KEY is still set to placeholder string.")
        return False

    # 2. Reset any mock instance
    EmbeddingService.set_embeddings_client(None)

    # 3. Connect to PostgreSQL
    print("\n[1/6] Connecting to PostgreSQL database...")
    try:
        db = SessionLocal()
        seed_roles(db)
        trainer_role = db.query(Role).filter(Role.name == RoleName.TRAINER.value).first()
        assert trainer_role is not None
        
        # Create or find a test trainer
        trainer = db.query(User).filter(User.email == "real_trainer@mospi.test").first()
        if not trainer:
            trainer = User(
                name="Real Test Trainer",
                email="real_trainer@mospi.test",
                password_hash="test_pwd_hash",
                role_id=trainer_role.id,
                department="Training Division",
                is_active=True,
            )
            db.add(trainer)
            db.commit()
            db.refresh(trainer)
        print(f"      Authenticated trainer user ID: {trainer.id}")
    except Exception as e:
        print(f"\n[FAILED] Database connection error: {e}")
        print("Please ensure PostgreSQL is running and DATABASE_URL in .env has the correct password.")
        return False

    # 4. Generate test PDF
    print("\n[2/6] Generating sample multi-page statistical PDF...")
    pdf_stream = generate_test_pdf_stream()
    upload_file = UploadFile(
        filename="nss_sampling_guidelines_real_test.pdf",
        file=pdf_stream,
        headers={"content-type": "application/pdf"},
    )
    print("      PDF generated: 2 pages of MoSPI NSS sampling content.")

    # 5. Execute upload and ingestion pipeline
    print("\n[3/6] Running DocumentService.upload_and_process() with REAL Mistral API...")
    try:
        doc = DocumentService.upload_and_process(
            db=db,
            upload_file=upload_file,
            current_user=trainer,
        )
    except Exception as e:
        print(f"\n[FAILED] Document ingestion exception: {e}")
        db.close()
        return False

    print(f"      Document ID: {doc.id}")
    print(f"      Document Status: {doc.status.value}")
    print(f"      Processing Error: {doc.processing_error}")

    if doc.status != DocumentStatus.PROCESSED:
        print(f"\n[FAILED] Document status is '{doc.status.value}', expected 'PROCESSED'!")
        print(f"         Error detail: {doc.processing_error}")
        db.close()
        return False

    # 6. Verify PostgreSQL chunks
    print("\n[4/6] Verifying PostgreSQL document_chunks table...")
    chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).order_by(DocumentChunk.chunk_index).all()
    print(f"      Total chunks persisted: {len(chunks)}")
    if len(chunks) == 0:
        print("\n[FAILED] Zero chunks persisted in PostgreSQL!")
        db.close()
        return False

    for c in chunks:
        print(f"      Chunk {c.chunk_index}: page={c.page_number}, chroma_id={c.chroma_id}")
        assert c.chroma_id is not None
        assert c.chroma_id.startswith(f"doc_{doc.id}_chunk_")

    # 7. Verify ChromaDB 1024-dimensional vectors
    print("\n[5/6] Verifying ChromaDB vector collection...")
    try:
        col = VectorStoreService.get_collection()
        chroma_ids = [c.chroma_id for c in chunks]
        res = col.get(ids=chroma_ids, include=["embeddings", "metadatas", "documents"])
        
        found_count = len(res["ids"])
        print(f"      Vectors found in ChromaDB: {found_count} of {len(chroma_ids)}")
        if found_count != len(chroma_ids):
            print(f"\n[FAILED] Vector count mismatch in ChromaDB! Expected {len(chroma_ids)}, found {found_count}")
            db.close()
            return False

        # Verify dimension
        embeddings = res.get("embeddings")
        if embeddings is not None and len(embeddings) > 0:
            actual_dim = len(embeddings[0])
            print(f"      Vector dimensionality: {actual_dim}")
            if actual_dim != 1024:
                print(f"\n[FAILED] Expected vector dimension 1024, got {actual_dim}!")
                db.close()
                return False
    except Exception as e:
        print(f"\n[FAILED] ChromaDB inspection failed: {e}")
        db.close()
        return False

    print("\n[6/6] Cleanup & verification status...")
    print(f"      Document ID {doc.id} is available for subsequent semantic search and MCQ tests.")
    db.close()

    print("\n" + "=" * 80)
    print("[SUCCESS] End-to-End Real PDF upload and Mistral vector ingestion verified!")
    print(f"          Document ID: {doc.id}")
    print(f"          Chunks Indexed: {len(chunks)}")
    print(f"          Vector Dimension: 1024")
    print("=" * 80)
    return True


if __name__ == "__main__":
    success = run_real_pdf_upload_test()
    sys.exit(0 if success else 1)
