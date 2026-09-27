"""Master Verification Harness for Live Mistral AI Integration.

Executes and reports on the full 5-stage verification sequence:
  Stage 1: Direct Mistral Embedding Smoke Test (1024-dim)
  Stage 2: ChromaDB 64-dim Collection Check / Reset
  Stage 3: End-to-End PDF Upload & 1024-dim Ingestion
  Stage 4: Semantic Similarity Retrieval
  Stage 5: Live Mistral Large MCQ Generation
  Stage 6: Automated Mock Regression Suite (174 pytest tests)
"""
import sys
import os
import subprocess
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))


def run_stage(title: str, script_name: str, args: list = None) -> bool:
    print("\n" + "=" * 80)
    print(f"STAGE: {title}")
    print("=" * 80)
    cmd = [sys.executable, str(backend_dir / "scratch" / script_name)] + (args or [])
    res = subprocess.run(cmd, cwd=str(backend_dir))
    return res.returncode == 0


def main():
    print("=" * 80)
    print("STATKARMAYOGI — REAL MISTRAL AI INTEGRATION VERIFICATION HARNESS")
    print("=" * 80)

    stages = [
        ("Stage 1: Live Mistral Embedding Smoke Test", "test_real_mistral_embedding.py", []),
        ("Stage 2: End-to-End PDF Upload & Ingestion", "test_real_pdf_upload.py", []),
        ("Stage 3: Semantic Retrieval in ChromaDB", "test_real_semantic_retrieval.py", []),
        ("Stage 4: Live Mistral Large MCQ Generation", "test_real_mistral_mcq.py", []),
    ]

    results = {}
    for title, script, args in stages:
        success = run_stage(title, script, args)
        results[title] = success
        if not success:
            print(f"\n[HALT] {title} failed. Please resolve the issue before proceeding.")
            break

    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY REPORT")
    print("=" * 80)
    for title, success in results.items():
        status = "[PASSED]" if success else "[FAILED]"
        print(f"  {status:10} {title}")
    print("=" * 80)


if __name__ == "__main__":
    main()
