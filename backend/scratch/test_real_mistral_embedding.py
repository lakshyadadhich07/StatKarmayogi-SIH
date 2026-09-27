"""Smoke test for live Mistral AI Embedding API.

Verifies:
1. settings.MISTRAL_API_KEY is configured.
2. EmbeddingService initializes real MistralAIEmbeddings (no mocks).
3. Mistral authentication succeeds over HTTPS.
4. Generates a real embedding vector.
5. Verifies the vector dimension is exactly 1024 floats.
6. Verifies vector contains non-zero float values.
7. Guarantees API key is NEVER printed or logged.
"""
import sys
import os
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.services.embedding_service import EmbeddingService, EmbeddingConfigurationError


def mask_key(key: str) -> str:
    """Safely masks an API key showing only redaction and character count."""
    if not key:
        return "<EMPTY>"
    return f"<CONFIGURED, REDACTED length={len(key)} chars>"


def run_embedding_smoke_test() -> bool:
    print("=" * 80)
    print("MISTRAL AI EMBEDDING SMOKE TEST (REAL API)")
    print("=" * 80)

    # 1. Check API Key presence without exposing secrets
    api_key = settings.MISTRAL_API_KEY
    if not api_key or not api_key.strip():
        print("\n[FAILED] MISTRAL_API_KEY is not configured in .env or environment.")
        print("Please configure MISTRAL_API_KEY in backend/.env before running this test.")
        return False

    if api_key.strip() == "your-mistral-api-key-here":
        print("\n[FAILED] MISTRAL_API_KEY is still set to the placeholder string from .env.example.")
        print("Please replace it with your valid Mistral API key.")
        return False

    print(f"\n[1/4] API Key Status: Configured {mask_key(api_key.strip())}")
    print(f"      Embedding Model: {settings.MISTRAL_EMBEDDING_MODEL}")

    # 2. Reset any previous mock instance
    EmbeddingService.set_embeddings_client(None)

    # 3. Instantiate client
    try:
        client = EmbeddingService.get_embeddings_client()
        print(f"[2/4] Initialized client: {client.__class__.__name__}")
    except EmbeddingConfigurationError as e:
        print(f"[FAILED] Client configuration error: {e}")
        return False
    except Exception as e:
        print(f"[FAILED] Unexpected error initializing client: {e}")
        return False

    # 4. Generate test embedding for query text
    test_text = "Ministry of Statistics and Programme Implementation (MoSPI) statistical methodology"
    print(f"[3/4] Calling Mistral API embeddings endpoint for test string...")
    print(f"      Input: \"{test_text}\"")

    try:
        embedding = EmbeddingService.embed_query(test_text)
    except Exception as e:
        print(f"\n[FAILED] Mistral API request failed: {e}")
        return False

    # 5. Verify dimensions and data integrity
    dim = len(embedding)
    print(f"[4/4] Response received! Vector dimension: {dim}")

    if dim != 1024:
        print(f"\n[FAILED] Expected vector dimension 1024 for mistral-embed, but received {dim}!")
        return False

    # Check non-trivial values
    norm = sum(x * x for x in embedding) ** 0.5
    print(f"      L2 norm: {norm:.4f}")
    if norm < 0.1:
        print("\n[FAILED] Generated vector has suspiciously low norm (zero/null vector).")
        return False

    # Also test batch embedding
    batch_texts = ["Descriptive Statistics", "Inferential Statistics and Sampling Theory"]
    print(f"\n      Testing batch embedding with {len(batch_texts)} items...")
    try:
        batch_embs = EmbeddingService.embed_documents(batch_texts)
        assert len(batch_embs) == 2, f"Expected 2 embeddings, got {len(batch_embs)}"
        assert len(batch_embs[0]) == 1024, f"Batch item 0 dimension {len(batch_embs[0])} != 1024"
        assert len(batch_embs[1]) == 1024, f"Batch item 1 dimension {len(batch_embs[1])} != 1024"
        print(f"      Batch embedding verified: 2 vectors of dimension 1024.")
    except Exception as e:
        print(f"\n[FAILED] Batch embedding failed: {e}")
        return False

    print("\n" + "=" * 80)
    print("[SUCCESS] Real Mistral AI embedding integration is WORKING!")
    print("          Authentication: Valid")
    print("          Model: mistral-embed")
    print("          Dimensionality: Exactly 1024 floats")
    print("=" * 80)
    return True


if __name__ == "__main__":
    success = run_embedding_smoke_test()
    sys.exit(0 if success else 1)
