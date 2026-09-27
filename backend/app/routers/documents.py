import logging
from typing import List
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import RoleName
from app.models.user import User
from app.schemas.document import (
    DocumentDetailResponse,
    DocumentResponse,
    DocumentSearchRequest,
    DocumentSearchResult,
)
from app.services.document_service import DocumentService
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and process a learning material document (PDF/PPT/PPTX)",
)
def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.TRAINER, RoleName.ADMIN)),
) -> DocumentResponse:
    """Uploads a PDF or PPTX document, saves it safely, extracts text preserving page/slide numbers,
    splits into deterministic chunks, and persists metadata in PostgreSQL.
    
    Restricted to TRAINER and ADMIN roles.
    """
    logger.info(f"User {current_user.id} ({current_user.role.name}) initiating upload of '{file.filename}'")
    document = DocumentService.upload_and_process(
        db=db,
        upload_file=file,
        current_user=current_user,
    )
    return DocumentResponse.model_validate(document)


@router.get(
    "",
    response_model=List[DocumentResponse],
    status_code=status.HTTP_200_OK,
    summary="List all uploaded learning documents",
)
def list_documents(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[DocumentResponse]:
    """Retrieves all accessible documents ordered by creation time descending.
    
    Accessible to all authenticated users.
    """
    documents = DocumentService.list_documents(db=db, skip=skip, limit=limit)
    return [DocumentResponse.model_validate(doc) for doc in documents]


@router.get(
    "/{document_id}",
    response_model=DocumentDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve document metadata and chunk count",
)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentDetailResponse:
    """Retrieves metadata and chunk count for a specific document without exposing internal filesystem paths."""
    document = DocumentService.get_document_by_id(db=db, document_id=document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found.",
        )
    chunk_count = DocumentService.get_chunk_count(db=db, document_id=document.id)

    doc_dict = {
        "id": document.id,
        "filename": document.filename,
        "file_type": document.file_type,
        "status": document.status,
        "uploaded_by": document.uploaded_by,
        "generation_count": document.generation_count,
        "processing_error": document.processing_error,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
        "chunk_count": chunk_count,
    }
    return DocumentDetailResponse.model_validate(doc_dict)


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a document and its stored file",
)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Deletes a document and its associated physical file.
    
    Only the original uploader or an ADMIN may delete the document.
    Deletion is prevented if questions are linked to the document.
    """
    document = DocumentService.get_document_by_id(db=db, document_id=document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found.",
        )

    DocumentService.delete_document(db=db, document=document, current_user=current_user)
    return {
        "message": "Document deleted successfully",
        "id": document_id,
    }


@router.post(
    "/search",
    response_model=List[DocumentSearchResult],
    status_code=status.HTTP_200_OK,
    summary="Semantic similarity search across indexed document chunks in ChromaDB",
)
def search_documents(
    request: DocumentSearchRequest,
    current_user: User = Depends(get_current_user),
) -> List[DocumentSearchResult]:
    """Performs semantic similarity search against the ChromaDB vector store.
    
    Uses Mistral Embeddings to vectorize the query text and retrieves top-k matching chunks.
    Protected by JWT authentication.
    """
    if not request.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query string cannot be empty.",
        )

    query_vector = EmbeddingService.embed_query(request.query)
    hits = VectorStoreService.similarity_search(
        query_embedding=query_vector,
        top_k=request.top_k,
        document_id=request.document_id,
    )
    return [DocumentSearchResult.model_validate(hit) for hit in hits]
