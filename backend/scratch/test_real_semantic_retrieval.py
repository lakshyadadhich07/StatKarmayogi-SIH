"""Verification script for semantic retrieval using real Mistral query embeddings.

Tests and verifies against Document ID 1102:
1. The search query is embedded using the REAL Mistral API.
2. The query embedding dimension is exactly 1024 floats.
3. ChromaDB accepts the query against the 1024-dimensional collection.
4. Similarity search executes successfully.
5. Results are returned with valid cosine/distance values.
6. Results are correctly ranked (monotonically non-decreasing distance).
7. Source document ID is correct (matches 1102).
8. Page number metadata is preserved correctly (Page 1 for FSU definition).
9. Chunk index and chunk content are returned correctly.
10. No mock embedding is used anywhere in this test.
"""
import sys
import os
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStoreService


def run_semantic_retrieval_test(target_doc_id: int = 1102) -> bool:
    print("=" * 80)
    print("REAL MISTRAL SEMANTIC RETRIEVAL TEST")
    print(f"Target Document ID: {target_doc_id}")
    print("=" * 80)

    # 1. Check API Key
    if not settings.MISTRAL_API_KEY or not settings.MISTRAL_API_KEY.strip():
        print("\n[FAILED] MISTRAL_API_KEY is not configured in .env.")
        return False

    # 2. Guarantee no mock embedding client is active (Point 10)
    EmbeddingService.set_embeddings_client(None)
    client = EmbeddingService.get_embeddings_client()
    print(f"\n[Check 10] Active embedding client: {client.__class__.__name__} (Real MistralAIEmbeddings, no mock)")
    assert client.__class__.__name__ == "MistralAIEmbeddings", f"Expected MistralAIEmbeddings, got {client.__class__.__name__}"

    # 3. Formulate query and embed using REAL Mistral API (Point 1)
    query = "What are the first stage units in rural areas?"
    print(f"\n[Check 1] Embedding query via live Mistral API:")
    print(f"          Query: \"{query}\"")

    try:
        query_vec = EmbeddingService.embed_query(query)
    except Exception as e:
        print(f"\n[FAILED] EmbeddingService.embed_query failed: {e}")
        return False

    # 4. Verify dimension is exactly 1024 (Point 2)
    dim = len(query_vec)
    print(f"[Check 2] Query vector dimension: {dim}")
    if dim != 1024:
        print(f"\n[FAILED] Expected query vector dimension 1024, got {dim}")
        return False
    assert dim == 1024

    # 5. ChromaDB similarity search (Points 3, 4, 7)
    print(f"\n[Check 3 & 4] Executing similarity search in ChromaDB filtered by document_id={target_doc_id}...")
    try:
        hits = VectorStoreService.similarity_search(
            query_embedding=query_vec,
            top_k=5,
            document_id=target_doc_id,
        )
    except Exception as e:
        print(f"\n[FAILED] ChromaDB similarity search failed: {e}")
        return False

    print(f"              Hits returned: {len(hits)}")
    if not hits:
        print(f"\n[FAILED] No hits returned for document_id={target_doc_id}!")
        return False

    # 6. Verify distance values and ranking (Points 5, 6)
    print("\n[Check 5 & 6] Validating distance values and ranking:")
    previous_dist = -1.0
    for idx, hit in enumerate(hits):
        dist = hit["distance"]
        print(f"      Rank #{idx + 1}: distance={dist:.6f} | chroma_id={hit['chroma_id']}")
        assert dist is not None, f"Hit {idx} distance is None!"
        assert isinstance(dist, (float, int)), f"Distance is not numeric: {type(dist)}"
        assert dist >= 0.0, f"Distance is negative: {dist}"
        if idx > 0:
            assert dist >= previous_dist, f"Hits not correctly ranked! Rank {idx} ({dist}) < Rank {idx-1} ({previous_dist})"
        previous_dist = dist

    print("      Ranking is strictly monotonic and valid.")

    # 7. Inspect top hit for document ID, page number, chunk index, and content (Points 7, 8, 9)
    top_hit = hits[0]
    print("\n[Check 7, 8, 9] Top-ranked matching chunk details:")
    print(f"      Chroma ID:    {top_hit['chroma_id']}")
    print(f"      Document ID:  {top_hit['document_id']}")
    print(f"      Chunk Index:  {top_hit['chunk_index']}")
    print(f"      Page Number:  {top_hit['page_number']}")
    print(f"      Filename:     {top_hit['filename']}")
    print(f"      Content:      {top_hit['content']}")

    # Assertions
    assert top_hit["document_id"] == target_doc_id, f"Document ID mismatch: expected {target_doc_id}, got {top_hit['document_id']}"
    assert top_hit["page_number"] == 1, f"Expected page number 1 for FSU definition, got {top_hit['page_number']}"
    assert top_hit["chunk_index"] == 0, f"Expected chunk index 0, got {top_hit['chunk_index']}"
    assert "Census villages" in top_hit["content"], "Expected 'Census villages' in chunk content!"
    assert "first stage units" in top_hit["content"].lower(), "Expected 'first stage units' in chunk content!"

    # 8. Also test unfiltered similarity search to verify global collection retrieval
    print("\n[Bonus Check] Executing unfiltered global similarity search across collection...")
    global_hits = VectorStoreService.similarity_search(query_embedding=query_vec, top_k=2)
    print(f"              Global hits returned: {len(global_hits)}")
    assert any(h["document_id"] in {1101, target_doc_id} for h in global_hits)

    print("\n" + "=" * 80)
    print("[SUCCESS] All 10 verification points for real semantic retrieval PASSED!")
    print(f"          Query Model: mistral-embed (1024 dimensions)")
    print(f"          Top Hit Chunk: {top_hit['chroma_id']}")
    print(f"          Top Hit Distance: {top_hit['distance']:.6f}")
    print(f"          Ground-Truth Match: \"Census villages in rural areas\"")
    print("=" * 80)
    return True


if __name__ == "__main__":
    target_id = 1102
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        target_id = int(sys.argv[1])
    success = run_semantic_retrieval_test(target_doc_id=target_id)
    sys.exit(0 if success else 1)
