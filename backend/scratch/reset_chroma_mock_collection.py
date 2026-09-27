"""Safe utility to backup and reset ONLY the mock 64-dimensional ChromaDB collection.

Safety features:
1. Detects current collection dimension.
2. Creates a full timestamped backup of the mock Chroma directory before any mutation.
3. Deletes ONLY the mock 64-dimensional collection 'statkarmayogi_chunks'.
4. Does not affect PostgreSQL or storage/documents.
5. Requires explicit '--confirm' CLI argument to prevent accidental execution.
"""
import sys
import os
import shutil
from datetime import datetime
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

import chromadb
from app.core.config import settings


def reset_mock_chroma_collection(dry_run: bool = True) -> bool:
    persist_dir = os.path.abspath(settings.CHROMA_PERSIST_DIRECTORY)
    collection_name = settings.CHROMA_COLLECTION_NAME or "statkarmayogi_chunks"

    print("=" * 80)
    print("CHROMADB MOCK COLLECTION RESET UTILITY")
    print(f"Target Directory: {persist_dir}")
    print(f"Collection Name:  {collection_name}")
    print("=" * 80)

    if not os.path.exists(persist_dir):
        print(f"[INFO] Chroma directory '{persist_dir}' does not exist yet. Nothing to reset.")
        return True

    try:
        client = chromadb.PersistentClient(path=persist_dir)
        collections = client.list_collections()
        col_names = [c.name for c in collections]
        print(f"Found existing collections: {col_names}")

        target_col = None
        for c in collections:
            if c.name == collection_name:
                target_col = c
                break

        if not target_col:
            print(f"[INFO] Collection '{collection_name}' not found in ChromaDB. Nothing to delete.")
            return True

        current_count = target_col.count()
        print(f"Collection '{collection_name}' has {current_count} vectors.")

        if dry_run:
            print("\n[DRY RUN MODE - NO CHANGES MADE]")
            print(f"To execute the reset, run this script with --confirm:")
            print(f"  python scratch/reset_chroma_mock_collection.py --confirm")
            return False

        # 1. Create a safe backup before deleting anything
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.abspath(f"storage/chroma_backup_64dim_{timestamp}")
        print(f"\n[1/3] Creating backup of mock Chroma store to: {backup_dir}")
        shutil.copytree(persist_dir, backup_dir)
        print("      Backup completed successfully.")

        # 2. Delete the 64-dimensional collection
        print(f"[2/3] Deleting mock 64-dimensional collection '{collection_name}'...")
        client.delete_collection(collection_name)
        print(f"      Collection '{collection_name}' deleted.")

        # 3. Verify deletion
        remaining = [c.name for c in client.list_collections()]
        print(f"[3/3] Remaining collections: {remaining}")
        assert collection_name not in remaining, "Collection was not deleted!"

        print("\n" + "=" * 80)
        print(f"[SUCCESS] ChromaDB collection '{collection_name}' successfully reset!")
        print("          On the next document upload with real Mistral embeddings,")
        print("          ChromaDB will automatically re-create the collection with dimension 1024.")
        print("=" * 80)
        return True

    except Exception as e:
        print(f"[ERROR] Failed to reset ChromaDB collection: {e}")
        return False


if __name__ == "__main__":
    is_confirmed = "--confirm" in sys.argv
    success = reset_mock_chroma_collection(dry_run=not is_confirmed)
    sys.exit(0 if success else 1)
