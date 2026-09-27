import hashlib
import logging
from typing import Any, Dict, List, Optional
from langchain_core.documents import Document as LCDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings

logger = logging.getLogger(__name__)


def compute_content_hash(text: str) -> str:
    """Computes a deterministic SHA-256 hexadecimal digest of the chunk text."""
    normalized = text.strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def split_documents_recursively(
    documents: List[LCDocument],
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> List[LCDocument]:
    """Uses LangChain's RecursiveCharacterTextSplitter for structure-preserving recursive splitting.
    
    Splits along paragraphs, line breaks, sentence delimiters, and word boundaries
    while preserving source document metadata.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""],
    )
    return splitter.split_documents(documents)


def create_chunks_from_documents(
    documents: List[LCDocument],
    document_id: int,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Splits LangChain documents into deterministic chunks with sequential indices,
    preserved page numbers, SHA-256 content hashes, and traceable Chroma IDs.
    """
    c_size = chunk_size or settings.CHUNK_SIZE or 1000
    c_overlap = chunk_overlap or settings.CHUNK_OVERLAP or 150

    split_docs = split_documents_recursively(
        documents=documents,
        chunk_size=c_size,
        chunk_overlap=c_overlap,
    )

    chunks: List[Dict[str, Any]] = []
    for idx, doc in enumerate(split_docs):
        text = doc.page_content.strip()
        if not text:
            continue

        c_hash = compute_content_hash(text)
        page_num = doc.metadata.get("page") or doc.metadata.get("page_number") or 1
        chroma_id = f"doc_{document_id}_chunk_{idx}_{c_hash[:16]}"

        chunks.append({
            "chunk_index": idx,
            "page_number": int(page_num),
            "content_hash": c_hash,
            "chroma_id": chroma_id,
            "text": text,
        })

    logger.info(f"Split {len(documents)} source pages into {len(chunks)} structure-preserving chunks.")
    return chunks
