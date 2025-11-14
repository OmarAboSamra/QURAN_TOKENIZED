"""
Complete workflow demonstration script.

This script demonstrates the full pipeline from tokenization to API serving.

Usage:
    python scripts/run_full_pipeline.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def main() -> None:
    """Run the complete pipeline."""
    import subprocess
    
    print("=" * 70)
    print("QURÁN ANALYSIS BACKEND - FULL PIPELINE DEMONSTRATION")
    print("=" * 70)
    print()
    
    scripts_dir = Path(__file__).parent
    
    # Stage 1: Tokenization
    print("🔹 STAGE 1: TOKENIZATION")
    print("-" * 70)
    result = subprocess.run(
        [sys.executable, str(scripts_dir / "tokenize_quran.py"), "--save-to-db"],
        cwd=scripts_dir.parent,
    )
    
    if result.returncode != 0:
        print("❌ Tokenization failed!")
        sys.exit(1)
    
    print()
    input("Press Enter to continue to Stage 2...")
    print()
    
    # Stage 2: Root Extraction (Placeholder)
    print("🔹 STAGE 2: ROOT EXTRACTION")
    print("-" * 70)
    print("Note: This stage uses placeholder extractors.")
    print("Implement actual API calls in backend/services/root_extractor.py")
    print()
    
    response = input("Run placeholder root extraction? (y/n): ")
    if response.lower() == 'y':
        result = subprocess.run(
            [sys.executable, str(scripts_dir / "fetch_roots.py"), "--limit", "10"],
            cwd=scripts_dir.parent,
        )
    
    print()
    input("Press Enter to continue to Stage 3...")
    print()
    
    # Stage 3: Reconcile Discrepancies
    print("🔹 STAGE 3: RECONCILE DISCREPANCIES")
    print("-" * 70)
    result = subprocess.run(
        [sys.executable, str(scripts_dir / "reconcile_roots.py")],
        cwd=scripts_dir.parent,
    )
    
    print()
    input("Press Enter to continue to Stage 4...")
    print()
    
    # Stage 4: Build References
    print("🔹 STAGE 4: BUILD REFERENCES")
    print("-" * 70)
    result = subprocess.run(
        [sys.executable, str(scripts_dir / "index_references.py")],
        cwd=scripts_dir.parent,
    )
    
    print()
    print("=" * 70)
    print("✅ PIPELINE COMPLETED SUCCESSFULLY!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("  1. Start the API server:")
    print("     python backend/main.py")
    print()
    print("  2. Access the API:")
    print("     - API: http://localhost:8000")
    print("     - Docs: http://localhost:8000/docs")
    print()
    print("  3. Try some endpoints:")
    print("     curl http://localhost:8000/meta/health")
    print("     curl http://localhost:8000/quran/verse/1/1")
    print("     curl http://localhost:8000/quran/stats")
    print()


if __name__ == "__main__":
    main()
