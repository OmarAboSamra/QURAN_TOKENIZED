"""Clear database for fresh tokenization."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.db import get_sync_session_maker
from backend.models import Token


def clear_database():
    """Clear all tokens from the database."""
    print("Clearing database...")
    
    session_maker = get_sync_session_maker()
    session = session_maker()
    
    try:
        # Count before deletion
        count_before = session.query(Token).count()
        print(f"  Current tokens: {count_before:,}")
        
        if count_before == 0:
            print("  Database is already empty.")
            return
        
        # Ask for confirmation
        response = input(f"\nAre you sure you want to delete {count_before:,} tokens? (yes/no): ")
        
        if response.lower() not in ['yes', 'y']:
            print("Cancelled.")
            return
        
        # Delete all tokens
        session.query(Token).delete()
        session.commit()
        
        # Verify
        count_after = session.query(Token).count()
        print(f"\n✓ Deleted {count_before:,} tokens")
        print(f"  Remaining tokens: {count_after}")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        session.rollback()
    finally:
        session.close()


if __name__ == "__main__":
    clear_database()
