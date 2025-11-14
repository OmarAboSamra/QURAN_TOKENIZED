"""
Script to reconcile root discrepancies and flag for manual review.

This script:
1. Reads tokens with multiple root sources
2. Compares results and detects conflicts
3. Updates token status based on agreement
4. Generates report of items needing review

Usage:
    python scripts/reconcile_roots.py
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.db import get_sync_session_maker, init_db
from backend.models import Token
from backend.services import DiscrepancyChecker


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Reconcile root extraction discrepancies"
    )
    parser.add_argument(
        "--min-sources",
        type=int,
        default=2,
        help="Minimum sources required for verification",
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Root Discrepancy Reconciliation Script")
    print("=" * 60)
    
    # Initialize database
    init_db()
    
    # Get tokens with root sources
    SessionMaker = get_sync_session_maker()
    with SessionMaker() as session:
        tokens = session.query(Token).filter(
            Token.root_sources.isnot(None)
        ).all()
        
        if not tokens:
            print("No tokens with root sources found.")
            print("Have you run fetch_roots.py?")
            sys.exit(0)
        
        print(f"Analyzing {len(tokens)} tokens...")
        print()
        
        # Initialize discrepancy checker
        checker = DiscrepancyChecker(
            min_sources_for_verification=args.min_sources
        )
        
        # Analyze each token
        updated = 0
        for token in tokens:
            if not token.root_sources:
                continue
            
            report = checker.check_discrepancy(
                token.normalized,
                token.root_sources,
            )
            
            # Update token
            token.root = report.consensus_root
            token.status = report.recommended_status
            updated += 1
        
        # Commit changes
        session.commit()
        
        # Get statistics
        stats = {
            "verified": session.query(Token).filter(
                Token.status == "verified"
            ).count(),
            "discrepancy": session.query(Token).filter(
                Token.status == "discrepancy"
            ).count(),
            "manual_review": session.query(Token).filter(
                Token.status == "manual_review"
            ).count(),
            "missing": session.query(Token).filter(
                Token.status == "missing"
            ).count(),
        }
        
        print("=" * 60)
        print(f"✓ Updated {updated} tokens")
        print()
        print("Status Summary:")
        print(f"  Verified:       {stats['verified']}")
        print(f"  Discrepancy:    {stats['discrepancy']}")
        print(f"  Manual Review:  {stats['manual_review']}")
        print(f"  Missing:        {stats['missing']}")
        print("=" * 60)


if __name__ == "__main__":
    main()
