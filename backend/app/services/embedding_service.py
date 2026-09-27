import logging
from typing import List, Optional
from langchain_mistralai import MistralAIEmbeddings

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingConfigurationError(Exception):
    """Raised when the Mistral embedding service is misconfigured or lacks required API credentials."""
    pass


class EmbeddingService:
    """Service wrapper for generating vector embeddings using Mistral AI."""

    _instance: Optional[MistralAIEmbeddings] = None

    @classmethod
    def get_embeddings_client(cls) -> MistralAIEmbeddings:
        """Instantiates or returns the configured MistralAIEmbeddings client.
        
        Validates that MISTRAL_API_KEY is present without logging secrets.
        """
        if cls._instance is not None:
            return cls._instance

        api_key = settings.MISTRAL_API_KEY
        if not api_key or not api_key.strip():
            logger.error("Mistral API key is missing from environment configuration.")
            raise EmbeddingConfigurationError(
                "MISTRAL_API_KEY is not configured. Please set MISTRAL_API_KEY in environment variables."
            )

        model_name = settings.MISTRAL_EMBEDDING_MODEL or "mistral-embed"
        logger.info(f"Initializing MistralAIEmbeddings with model '{model_name}'")

        cls._instance = MistralAIEmbeddings(
            model=model_name,
            api_key=api_key.strip(),
        )
        return cls._instance

    @classmethod
    def set_embeddings_client(cls, client: Optional[MistralAIEmbeddings]) -> None:
        """Allows overriding or mocking the embeddings client for tests."""
        cls._instance = client

    @classmethod
    def embed_documents(cls, texts: List[str]) -> List[List[float]]:
        """Generates embeddings for a batch of chunk texts.
        
        Embedding dimensionality is determined dynamically by the model response.
        """
        if not texts:
            return []

        client = cls.get_embeddings_client()
        try:
            embeddings = client.embed_documents(texts)
            if embeddings and len(embeddings) > 0:
                dim = len(embeddings[0])
                logger.info(f"Generated {len(embeddings)} embeddings with dynamic dimension {dim}")
            return embeddings
        except EmbeddingConfigurationError:
            raise
        except Exception as e:
            logger.error(f"Error generating Mistral embeddings: {e}")
            raise RuntimeError(f"Mistral embedding generation failed: {str(e)}")

    @classmethod
    def embed_query(cls, query: str) -> List[float]:
        """Generates an embedding vector for a search query string."""
        if not query or not query.strip():
            return []

        client = cls.get_embeddings_client()
        try:
            return client.embed_query(query.strip())
        except EmbeddingConfigurationError:
            raise
        except Exception as e:
            logger.error(f"Error generating query embedding: {e}")
            raise RuntimeError(f"Mistral query embedding failed: {str(e)}")
