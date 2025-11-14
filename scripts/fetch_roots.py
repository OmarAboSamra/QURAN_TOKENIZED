"""
Offline script to fetch Arabic roots from multiple sources.

This script:
1. Reads tokens from the database
2. Queries multiple online sources for root extraction
3. Caches results locally
4. Updates database with root information

Usage:
    python scripts/fetch_roots.py
    python scripts/fetch_roots.py --limit 100
    python scripts/fetch_roots.py --sources qurancorpus,tanzil
"""
import argparse
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import get_settings
from backend.db import get_sync_session_maker, init_db
from backend.models import Token, TokenStatus
from backend.services import RootExtractionService


def main() -> None:
    """Main entry point for root extraction script."""
    parser = argparse.ArgumentParser(
        description="Extract Arabic roots from multiple sources"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of tokens to process (for testing)",
    )
    parser.add_argument(
        "--sources",
        type=str,
        help="Comma-separated list of sources (default: all configured)",
    )
    parser.add_argument(
        "--sura",
        type=int,
        help="Process only specific sura",
    )
    
    args = parser.parse_args()
    settings = get_settings()
    
    print("=" * 60)
    print("Root Extraction Script")
    print("=" * 60)
    
    # Initialize database
    init_db()
    
    # Get tokens from database
    SessionMaker = get_sync_session_maker()
    with SessionMaker() as session:
        query = session.query(Token).filter(Token.root.is_(None))
        
        if args.sura:
            query = query.filter(Token.sura == args.sura)
        
        if args.limit:
            query = query.limit(args.limit)
        
        tokens = query.all()
        
        if not tokens:
            print("No tokens found that need root extraction.")
            print("Have you run tokenize_quran.py with --save-to-db flag?")
            sys.exit(0)
        
        print(f"Found {len(tokens)} tokens to process")
        print()
    
    # Determine sources
    sources = None
    if args.sources:
        sources = [s.strip() for s in args.sources.split(",")]
        print(f"Using sources: {', '.join(sources)}")
    else:
        print(f"Using configured sources: {', '.join(settings.root_sources_list)}")
    
    print()
    
    # Initialize root extraction service
    cache_path = Path(settings.root_cache_path)
    root_service = RootExtractionService(cache_path=cache_path)
    
    print("Starting root extraction...")
    print(f"Using fallback data for Surah 1 words")
    print()
    
    # Process tokens
    async def process_tokens() -> None:
        """Process all tokens asynchronously."""
        processed = 0
        updated = 0
        
        for i, token in enumerate(tokens, 1):
            if i % 10 == 0 or i == 1:
                print(f"Progress: {i}/{len(tokens)} tokens processed... ({updated} updated)")
            
            # Extract roots from multiple sources
            results = await root_service.extract_root_multi_source(
                token.normalized,
                sources=sources,
            )
            
            # Check if we got any successful results
            successful_results = {
                source: result.root 
                for source, result in results.items() 
                if result.success and result.root
            }
            
            if successful_results:
                # Store in token.root_sources
                token.root_sources = successful_results
                
                # Use the first successful result as the root
                token.root = list(successful_results.values())[0]
                token.status = TokenStatus.VERIFIED.value if len(successful_results) > 1 else TokenStatus.MISSING.value
                
                updated += 1
                
                print(f"  ✓ {token.text_ar} ({token.normalized}) → {token.root}")
            
            processed += 1
            
            # Small delay to avoid overwhelming APIs (if real APIs were used)
            await asyncio.sleep(0.05)
        
        return processed, updated
    
    # Run async processing
    try:
        processed, updated = asyncio.run(process_tokens())
        
        # Save to database
        with SessionMaker() as session:
            for token in tokens:
                if token.root:
                    session.merge(token)
            session.commit()
        
        # Save cache
        root_service.save_cache()
        
        print()
        print("=" * 60)
        print(f"✓ Root extraction completed")
        print(f"  Processed: {processed} tokens")
        print(f"  Updated:   {updated} tokens with roots")
        print(f"✓ Cache saved to: {cache_path}")
        print("=" * 60)
        print()
        print("Next steps:")
        print("  1. Reconcile discrepancies: python scripts/reconcile_roots.py")
        print("  2. Build references: python scripts/index_references.py")
        print("  3. Start API server: python backend/main.py")
        print("  4. View demo: http://localhost:8000/demo")
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        root_service.save_cache()
        sys.exit(1)


if __name__ == "__main__":
    main()
