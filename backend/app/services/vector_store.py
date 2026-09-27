import logging
import os
from typing import Any, Dict, List, Optional
import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection

from app.core.config import settings

logger = logging.getLogger(__name__)


class VectorStoreService:
    """Service managing ChromaDB persistent client, collections, indexing, and vector retrieval."""

    _client: Optional[ClientAPI] = None

    @classmethod
    def get_client(cls) -> ClientAPI:
        """Initializes or returns the persistent ChromaDB client."""
        if cls._client is not None:
            return cls._client

        persist_dir = os.path.abspath(settings.CHROMA_PERSIST_DIRECTORY)
        os.makedirs(persist_dir, exist_ok=True)
        logger.info(f"Connecting to persistent ChromaDB at '{persist_dir}'")
        cls._client = chromadb.PersistentClient(path=persist_dir)
        return cls._client

    @classmethod
    def set_client(cls, client: Optional[ClientAPI]) -> None:
        """Allows injecting an isolated or temporary ChromaDB client for tests."""
        cls._client = client

    @classmethod
    def get_collection(cls, collection_name: Optional[str] = None) -> Collection:
        """Retrieves or creates the dedicated StatKarmayogi ChromaDB collection."""
        client = cls.get_client()
        name = collection_name or settings.CHROMA_COLLECTION_NAME or "statkarmayogi_chunks"
        return client.get_or_create_collection(
            name=name,
            metadata={"description": "StatKarmayogi Document Chunks and Embeddings"},
        )

    @classmethod
    def add_chunks(
        cls,
        document_id: int,
        filename: str,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]],
    ) -> List[str]:
        """Upserts chunk vectors and metadata into ChromaDB with deterministic traceable IDs.
        
        Traceable ID pattern: doc_{document_id}_chunk_{chunk_index}_{content_hash[:16]}
        Returns list of generated chroma_id strings.
        """
        if not chunks:
            return []

        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Mismatch: {len(chunks)} chunks provided but received {len(embeddings)} embeddings."
            )

        collection = cls.get_collection()

        ids: List[str] = []
        documents_text: List[str] = []
        metadatas: List[Dict[str, Any]] = []

        for chunk in chunks:
            c_idx = chunk["chunk_index"]
            c_hash = chunk["content_hash"]
            c_page = chunk.get("page_number") or 1
            c_text = chunk.get("text", "")

            # Deterministic, traceable Chroma document ID
            chroma_id = f"doc_{document_id}_chunk_{c_idx}_{c_hash[:16]}"
            ids.append(chroma_id)
            documents_text.append(c_text)

            meta: Dict[str, Any] = {
                "document_id": document_id,
                "chunk_index": c_idx,
                "page_number": int(c_page),
                "content_hash": c_hash,
                "filename": filename,
            }
            metadatas.append(meta)

        try:
            # Use upsert to ensure idempotency across reprocessing
            collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents_text,
                metadatas=metadatas,
            )
            logger.info(
                f"Successfully upserted {len(ids)} vectors for document {document_id} into ChromaDB collection '{collection.name}'"
            )
            return ids
        except Exception as e:
            logger.error(f"Failed to upsert vectors into ChromaDB for document {document_id}: {e}")
            raise RuntimeError(f"ChromaDB indexing failed: {str(e)}")

    @classmethod
    def delete_by_ids(cls, ids: List[str]) -> None:
        """Deletes specific vectors by their Chroma IDs (used for failure compensation)."""
        if not ids:
            return
        collection = cls.get_collection()
        try:
            collection.delete(ids=ids)
            logger.info(f"Purged {len(ids)} vectors from ChromaDB as compensation.")
        except Exception as e:
            logger.warning(f"Error purging ChromaDB vectors {ids}: {e}")

    @classmethod
    def delete_document_vectors(cls, document_id: int) -> int:
        """Removes all vectors belonging to a document from ChromaDB."""
        collection = cls.get_collection()
        try:
            # Query existing IDs for the document to accurately log count
            results = collection.get(
                where={"document_id": document_id},
                include=[],
            )
            found_ids = results.get("ids", [])
            if found_ids:
                collection.delete(ids=found_ids)
                logger.info(
                    f"Deleted {len(found_ids)} vectors for document {document_id} from ChromaDB"
                )
                return len(found_ids)
            return 0
        except Exception as e:
            logger.warning(f"Error deleting ChromaDB vectors for document {document_id}: {e}")
            return 0

    @classmethod
    def similarity_search(
        cls,
        query_embedding: List[float],
        top_k: int = 5,
        document_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Queries ChromaDB using the query vector with optional document_id filter."""
        collection = cls.get_collection()
        where_filter: Optional[Dict[str, Any]] = None
        if document_id is not None:
            where_filter = {"document_id": document_id}

        try:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_filter,
                include=["documents", "metadatas", "distances"],
            )

            hits: List[Dict[str, Any]] = []
            ids_list = results.get("ids", [[]])[0]
            docs_list = results.get("documents", [[]])[0]
            metas_list = results.get("metadatas", [[]])[0]
            dists_list = results.get("distances", [[]])[0]

            for i in range(len(ids_list)):
                meta = metas_list[i] if i < len(metas_list) else {}
                hits.append({
                    "chroma_id": ids_list[i],
                    "content": docs_list[i] if i < len(docs_list) else "",
                    "document_id": meta.get("document_id"),
                    "chunk_index": meta.get("chunk_index"),
                    "page_number": meta.get("page_number"),
                    "content_hash": meta.get("content_hash"),
                    "filename": meta.get("filename"),
                    "distance": dists_list[i] if i < len(dists_list) else None,
                })
            return hits
        except Exception as e:
            logger.error(f"Error during ChromaDB similarity search: {e}")
            raise RuntimeError(f"ChromaDB similarity search failed: {str(e)}")
