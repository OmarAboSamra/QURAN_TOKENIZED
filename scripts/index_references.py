"""
Script to build reference index linking tokens by root.

This script:
1. Groups all tokens by their verified root
2. Creates bidirectional references
3. Updates both Token and Root tables
4. Optimizes for efficient lookups

Usage:
    python scripts/index_references.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.db import get_sync_session_maker, init_db
from backend.models import Root, Token
from backend.services import ReferenceLinker


def main() -> None:
    """Main entry point."""
    print("=" * 60)
    print("Reference Indexing Script")
    print("=" * 60)
    
    # Initialize database
    init_db()
    
    # Get all tokens with roots
    SessionMaker = get_sync_session_maker()
    with SessionMaker() as session:
        tokens = session.query(Token).filter(Token.root.isnot(None)).all()
        
        if not tokens:
            print("No tokens with roots found.")
            print("Have you run reconcile_roots.py?")
            sys.exit(0)
        
        print(f"Processing {len(tokens)} tokens...")
        print()
        
        # Initialize reference linker
        linker = ReferenceLinker()
        
        # Build root index
        token_data = [
            (token.id, token.normalized, token.root)
            for token in tokens
        ]
        
        root_index = linker.build_root_index(token_data)
        print(f"✓ Built index for {len(root_index)} unique roots")
        
        # Build token references
        token_references = linker.build_token_references(root_index)
        
        # Compress references for large groups
        token_references = linker.compress_references(
            token_references,
            max_references=100,
        )
        print(f"✓ Built references for {len(token_references)} tokens")
        
        # Update Token table with references
        for token in tokens:
            if token.id in token_references:
                token.references = token_references[token.id]
        
        # Update or create Root entries
        for root, token_ids in root_index.items():
            root_obj = session.query(Root).filter(Root.root == root).first()
            
            if root_obj:
                root_obj.tokens = token_ids
                root_obj.token_count = len(token_ids)
            else:
                root_obj = Root(
                    root=root,
                    tokens=token_ids,
                    token_count=len(token_ids),
                )
                session.add(root_obj)
        
        # Commit changes
        session.commit()
        
        # Get statistics
        stats = linker.get_statistics(root_index)
        
        print()
        print("=" * 60)
        print("✓ Reference indexing completed")
        print()
        print("Statistics:")
        print(f"  Total roots:           {stats['total_roots']}")
        print(f"  Total tokens indexed:  {stats['total_tokens']}")
        print(f"  Avg tokens per root:   {stats['avg_tokens_per_root']:.1f}")
        print(f"  Max tokens per root:   {stats['max_tokens_per_root']}")
        print(f"  Min tokens per root:   {stats['min_tokens_per_root']}")
        print("=" * 60)


if __name__ == "__main__":
    main()
