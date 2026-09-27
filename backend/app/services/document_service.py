import logging
import os
import re
import uuid
from typing import List, Optional, Tuple
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.enums import DocumentStatus, RoleName
from app.models.question import Question
from app.models.user import User
from app.services.document_chunker import create_chunks_from_documents
from app.services.document_parser import (
    DocumentParsingError,
    EmptyDocumentError,
    load_document_pages,
)
from app.services.embedding_service import (
    EmbeddingConfigurationError,
    EmbeddingService,
)
from app.services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".pdf", ".pptx", ".ppt"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/x-pdf",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.ms-powerpoint",
    "application/powerpoint",
    "application/octet-stream",
    "application/zip",
    "application/x-zip-compressed",
}


class DocumentService:
    """Service orchestrating document lifecycle, LangChain loading, text splitting,
    Mistral vector embedding, ChromaDB indexing, and PostgreSQL traceability.
    """

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitizes an uploaded filename to prevent directory traversal and invalid characters."""
        base = os.path.basename(filename or "document")
        sanitized = re.sub(r"[^\w\.\-]", "_", base)
        sanitized = sanitized.lstrip(".")
        if not sanitized:
            sanitized = "uploaded_file"
        return sanitized

    @staticmethod
    def validate_file_metadata(upload_file: UploadFile) -> Tuple[str, str]:
        """Validates file extension and MIME type.
        
        Returns:
            Tuple of (sanitized_original_filename, normalized_extension_without_dot)
        """
        raw_filename = upload_file.filename or ""
        ext = os.path.splitext(raw_filename)[1].lower()

        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file extension '{ext}'. Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
            )

        content_type = upload_file.content_type
        if content_type and content_type.lower() not in ALLOWED_MIME_TYPES:
            logger.warning(
                f"Unusual MIME type '{content_type}' for filename '{raw_filename}' with extension '{ext}'"
            )

        sanitized_name = DocumentService.sanitize_filename(raw_filename)
        return sanitized_name, ext.lstrip(".")

    @staticmethod
    def save_upload_to_storage(upload_file: UploadFile, sanitized_name: str) -> str:
        """Streams upload file to storage directory while enforcing MAX_UPLOAD_SIZE_MB."""
        upload_dir = os.path.abspath(settings.UPLOAD_DIR)
        os.makedirs(upload_dir, exist_ok=True)

        unique_server_name = f"{uuid.uuid4().hex}_{sanitized_name}"
        dest_path = os.path.join(upload_dir, unique_server_name)

        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        total_bytes = 0

        try:
            upload_file.file.seek(0)
            with open(dest_path, "wb") as buffer:
                while True:
                    chunk = upload_file.file.read(1024 * 64)
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    if total_bytes > max_bytes:
                        buffer.close()
                        if os.path.exists(dest_path):
                            os.remove(dest_path)
                        raise HTTPException(
                            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                            detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB.",
                        )
                    buffer.write(chunk)
        except HTTPException:
            raise
        except Exception as e:
            if os.path.exists(dest_path):
                os.remove(dest_path)
            logger.error(f"Error saving upload file to {dest_path}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save uploaded file to storage.",
            )

        logger.info(f"Uploaded file saved to {dest_path} ({total_bytes} bytes)")
        return dest_path

    @classmethod
    def upload_and_process(
        cls,
        db: Session,
        upload_file: UploadFile,
        current_user: User,
    ) -> Document:
        """Executes the full document ingestion pipeline:
        1. File validation and storage
        2. Document record creation (status = UPLOADED -> PROCESSING)
        3. LangChain document loading (PyPDFLoader / python-pptx converter)
        4. Structure-preserving recursive splitting (RecursiveCharacterTextSplitter)
        5. Mistral AI embedding generation
        6. ChromaDB vector indexing with deterministic IDs
        7. PostgreSQL chunk persistence with chroma_id traceability
        8. Explicit failure compensation (purging Chroma vectors if PostgreSQL persistence fails)
        """
        sanitized_name, file_ext = cls.validate_file_metadata(upload_file)
        dest_path = cls.save_upload_to_storage(upload_file, sanitized_name)

        document = Document(
            uploaded_by=current_user.id,
            filename=sanitized_name,
            file_type=file_ext.upper(),
            file_path=dest_path,
            status=DocumentStatus.UPLOADED,
            generation_count=0,
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        logger.info(f"Created document record ID {document.id} with status UPLOADED")

        document.status = DocumentStatus.PROCESSING
        db.commit()
        logger.info(f"Document {document.id} status transitioned to PROCESSING")

        inserted_chroma_ids: List[str] = []

        try:
            # 1. Load document via LangChain (PyPDFLoader for PDF or python-pptx for PPTX)
            lc_docs = load_document_pages(dest_path, file_ext)

            # 2. Structure-preserving recursive splitting
            chunks = create_chunks_from_documents(
                documents=lc_docs,
                document_id=document.id,
                chunk_size=settings.CHUNK_SIZE,
                chunk_overlap=settings.CHUNK_OVERLAP,
            )

            # 3. Generate Mistral Embeddings
            chunk_texts = [c["text"] for c in chunks]
            embeddings = EmbeddingService.embed_documents(chunk_texts)

            # 4. Index vectors in ChromaDB
            inserted_chroma_ids = VectorStoreService.add_chunks(
                document_id=document.id,
                filename=document.filename,
                chunks=chunks,
                embeddings=embeddings,
            )

            # 5. Persist chunk metadata and chroma_id in PostgreSQL
            for idx, chunk in enumerate(chunks):
                assigned_chroma_id = inserted_chroma_ids[idx]
                chunk_entity = DocumentChunk(
                    document_id=document.id,
                    chunk_index=chunk["chunk_index"],
                    page_number=chunk["page_number"],
                    content_hash=chunk["content_hash"],
                    chroma_id=assigned_chroma_id,
                )
                db.add(chunk_entity)

            document.status = DocumentStatus.PROCESSED
            document.processing_error = None
            db.commit()
            db.refresh(document)
            logger.info(
                f"Document {document.id} successfully processed: {len(chunks)} chunks indexed in ChromaDB and persisted in PostgreSQL."
            )
            return document

        except EmptyDocumentError as ede:
            db.rollback()
            document.status = DocumentStatus.FAILED
            document.processing_error = str(ede)
            db.commit()
            db.refresh(document)
            logger.warning(f"Document {document.id} failed empty document check: {ede}")
            return document

        except EmbeddingConfigurationError as ece:
            db.rollback()
            document.status = DocumentStatus.FAILED
            document.processing_error = f"Embedding configuration error: {str(ece)}"
            db.commit()
            db.refresh(document)
            logger.error(f"Document {document.id} embedding configuration failed: {ece}")
            return document

        except Exception as e:
            # Explicit failure compensation (User Correction 2)
            logger.error(f"Document {document.id} processing failed: {e}")
            if inserted_chroma_ids:
                logger.info(
                    f"Compensating failure: purging {len(inserted_chroma_ids)} vectors from ChromaDB for document {document.id}"
                )
                try:
                    VectorStoreService.delete_by_ids(inserted_chroma_ids)
                except Exception as comp_err:
                    logger.critical(f"ChromaDB compensation purge failed: {comp_err}")

            db.rollback()
            # Fresh transaction to record failure status
            document.status = DocumentStatus.FAILED
            document.processing_error = f"Processing error: {str(e)[:500]}"
            db.commit()
            db.refresh(document)
            return document

    @staticmethod
    def list_documents(
        db: Session,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Document]:
        """Returns documents ordered by creation date descending."""
        return (
            db.query(Document)
            .order_by(Document.id.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_document_by_id(db: Session, document_id: int) -> Optional[Document]:
        """Fetch document by primary key."""
        return db.query(Document).filter(Document.id == document_id).first()

    @staticmethod
    def get_chunk_count(db: Session, document_id: int) -> int:
        """Count persisted chunks for a given document."""
        return db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).count()

    @staticmethod
    def delete_document(
        db: Session,
        document: Document,
        current_user: User,
    ) -> None:
        """Deletes a document and its stored vectors/file, ensuring synchronization and integrity."""
        is_uploader = document.uploaded_by == current_user.id
        is_admin = bool(current_user.role and current_user.role.name == RoleName.ADMIN.value)

        if not (is_uploader or is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to delete this document.",
            )

        linked_questions_count = (
            db.query(Question.id)
            .filter(Question.document_id == document.id)
            .count()
        )
        if linked_questions_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete document because associated questions exist.",
            )

        file_path = document.file_path

        # 1. Remove vectors from ChromaDB first
        try:
            VectorStoreService.delete_document_vectors(document.id)
        except Exception as e:
            logger.warning(f"Error purging ChromaDB vectors during deletion of document {document.id}: {e}")

        # 2. Delete database record (cascades to document_chunks)
        db.delete(document)
        db.commit()
        logger.info(f"Deleted Document record {document.id} from database")

        # 3. Remove physical file
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Deleted physical file from storage: {file_path}")
            except Exception as e:
                logger.warning(f"Could not delete physical file {file_path}: {e}")
