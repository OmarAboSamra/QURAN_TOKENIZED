"""
Backup placeholder roots and clear database for verified extraction.

This script:
1. Backs up quran_roots_comprehensive.json to quran_roots_placeholder_backup.json
2. Clears all root fields in the database
3. Updates status to 'missing' for all tokens
4. Creates a checkpoint for rollback if needed
"""

import shutil
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.db import get_sync_session_maker
from backend.models import Token
from backend.logging_config import get_logger

logger = get_logger(__name__)


def main():
    """Main execution function."""
    print("=" * 70)
    print("Database Cleanup: Preparing for Verified Root Extraction")
    print("=" * 70)
    
    # Step 1: Backup placeholder roots file
    print("\n[1/4] Backing up placeholder roots...")
    
    data_dir = Path(__file__).parent.parent / "data"
    comprehensive_file = data_dir / "quran_roots_comprehensive.json"
    backup_file = data_dir / "quran_roots_placeholder_backup.json"
    timestamp_backup = data_dir / f"quran_roots_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    if comprehensive_file.exists():
        # Create timestamped backup
        shutil.copy2(comprehensive_file, timestamp_backup)
        print(f"  ✓ Created timestamped backup: {timestamp_backup.name}")
        
        # Create named backup
        shutil.copy2(comprehensive_file, backup_file)
        print(f"  ✓ Created named backup: {backup_file.name}")
    else:
        print(f"  ⚠ No comprehensive file found at: {comprehensive_file}")
    
    # Step 2: Query current statistics
    print("\n[2/4] Checking current database state...")
    
    SessionMaker = get_sync_session_maker()
    
    with SessionMaker() as session:
        # Count total tokens
        total_tokens = session.query(Token).count()
        
        # Count tokens with roots
        tokens_with_roots = session.query(Token).filter(
            Token.root != None,
            Token.root != ""
        ).count()
        
        # Count by sura
        sura_1_total = session.query(Token).filter(Token.sura == 1).count()
        sura_1_with_roots = session.query(Token).filter(
            Token.sura == 1,
            Token.root != None,
            Token.root != ""
        ).count()
        
        sura_2_total = session.query(Token).filter(Token.sura == 2).count()
        sura_2_with_roots = session.query(Token).filter(
            Token.sura == 2,
            Token.root != None,
            Token.root != ""
        ).count()
        
        print(f"\n  Current Statistics:")
        print(f"  - Total tokens: {total_tokens}")
        print(f"  - Tokens with roots: {tokens_with_roots} ({tokens_with_roots/total_tokens*100:.1f}%)")
        print(f"  - Sura 1: {sura_1_with_roots}/{sura_1_total} ({sura_1_with_roots/sura_1_total*100:.1f}%)")
        print(f"  - Sura 2: {sura_2_with_roots}/{sura_2_total} ({sura_2_with_roots/sura_2_total*100:.1f}%)")
    
    # Step 3: Confirm with user
    print("\n[3/4] Ready to clear placeholder roots...")
    print("\n  ⚠ WARNING: This will clear all root data from the database!")
    print("  This operation is REVERSIBLE using the backup files.")
    print()
    
    response = input("  Continue? [y/N]: ").strip().lower()
    
    if response != 'y':
        print("\n  Operation cancelled by user.")
        return
    
    # Step 4: Clear database
    print("\n[4/4] Clearing roots from database...")
    
    with SessionMaker() as session:
        try:
            # Update all tokens: clear root and status
            result = session.query(Token).update(
                {
                    Token.root: None,
                    Token.status: "missing"
                },
                synchronize_session=False
            )
            
            session.commit()
            
            print(f"  ✓ Cleared roots from {result} tokens")
            print(f"  ✓ Updated status to 'missing'")
            
            # Verify
            remaining_with_roots = session.query(Token).filter(
                Token.root != None,
                Token.root != ""
            ).count()
            
            if remaining_with_roots == 0:
                print(f"  ✓ Verification passed: 0 tokens with roots remaining")
            else:
                print(f"  ⚠ Warning: {remaining_with_roots} tokens still have roots")
                
        except Exception as e:
            session.rollback()
            print(f"  ✗ Error: {e}")
            raise
    
    # Final summary
    print("\n" + "=" * 70)
    print("Cleanup Complete!")
    print("=" * 70)
    print("\nNext steps:")
    print("  1. Start Celery worker: .\\scripts\\start_celery_worker.ps1")
    print("  2. Start FastAPI server: uvicorn backend.main:app --reload")
    print("  3. Trigger extraction:")
    print("     POST http://localhost:8000/pipeline/extract-roots?sura=1&chunk_size=50")
    print("     POST http://localhost:8000/pipeline/extract-roots?sura=2&chunk_size=50")
    print("\nTo restore placeholder roots (if needed):")
    print(f"  cp {backup_file} {comprehensive_file}")
    print("  # Then re-run extraction pipeline")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        sys.exit(1)
