from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

from app.models.enums import DocumentStatus


class DocumentResponse(BaseModel):
    """Safe document metadata response schema."""

    id: int
    filename: str
    file_type: str
    status: DocumentStatus
    uploaded_by: int
    generation_count: int
    processing_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentDetailResponse(DocumentResponse):
    """Detailed document response including chunk count."""

    chunk_count: int = 0


class DocumentChunkResponse(BaseModel):
    """Metadata representation for a single document chunk."""

    id: int
    document_id: int
    chunk_index: int
    page_number: Optional[int] = None
    content_hash: Optional[str] = None
    chroma_id: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentSearchRequest(BaseModel):
    """Request schema for semantic vector similarity search."""

    query: str
    document_id: Optional[int] = None
    top_k: int = 5


class DocumentSearchResult(BaseModel):
    """Result schema for semantic vector similarity search."""

    chroma_id: str
    content: str
    document_id: Optional[int] = None
    chunk_index: Optional[int] = None
    page_number: Optional[int] = None
    content_hash: Optional[str] = None
    filename: Optional[str] = None
    distance: Optional[float] = None
