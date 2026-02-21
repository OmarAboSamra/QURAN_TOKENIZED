"""
Service for building reference links between tokens sharing the same root.

After roots are extracted and verified, this service groups tokens by root
and creates bidirectional cross-references. This enables the core analysis
use case: "show me all other places where a word from root X appears."

Pipeline:
    1. build_root_index()        – root → [token_id, ...]
    2. build_token_references()  – token_id → [related_token_ids, ...]
    3. compress_references()     – cap at max_references per token

The compressed references are stored in Token.references (JSON column).
"""
from collections import defaultdict
from typing import Optional


class ReferenceLinker:
    """
    Service for building reference links between tokens.
    
    This service:
    - Groups tokens by their root
    - Creates bidirectional references
    - Optimizes storage for fast lookup
    """

    def __init__(self) -> None:
        """Initialize reference linker."""
        pass

    def build_root_index(
        self,
        tokens: list[tuple[int, str, Optional[str]]],
    ) -> dict[str, list[int]]:
        """
        Build an index mapping roots to token IDs.
        
        Args:
            tokens: List of tuples (token_id, word, root)
            
        Returns:
            Dictionary mapping root to list of token IDs
        """
        root_index: dict[str, list[int]] = defaultdict(list)
        
        for token_id, word, root in tokens:
            if root:
                root_index[root].append(token_id)
        
        # Convert to regular dict and sort token IDs
        return {
            root: sorted(token_ids) for root, token_ids in root_index.items()
        }

    def build_token_references(
        self,
        root_index: dict[str, list[int]],
    ) -> dict[int, list[int]]:
        """
        Build references for each token to other tokens with the same root.
        
        Args:
            root_index: Dictionary mapping root to list of token IDs
            
        Returns:
            Dictionary mapping token_id to list of related token IDs
        """
        token_references: dict[int, list[int]] = {}
        
        for root, token_ids in root_index.items():
            # For each token, create references to all other tokens with same root
            for token_id in token_ids:
                # Exclude self from references
                references = [tid for tid in token_ids if tid != token_id]
                token_references[token_id] = references
        
        return token_references

    def compress_references(
        self,
        token_references: dict[int, list[int]],
        max_references: int = 100,
    ) -> dict[int, list[int]]:
        """
        Compress references by limiting the number stored per token.
        
        For tokens with many references, store a sample rather than all.
        
        Args:
            token_references: Full reference dictionary
            max_references: Maximum number of references to store per token
            
        Returns:
            Compressed reference dictionary
        """
        compressed: dict[int, list[int]] = {}
        
        for token_id, references in token_references.items():
            if len(references) <= max_references:
                compressed[token_id] = references
            else:
                # Store first, middle, and last references
                step = len(references) // (max_references - 1)
                sampled = references[::step][:max_references]
                compressed[token_id] = sampled
        
        return compressed

    def get_statistics(
        self,
        root_index: dict[str, list[int]],
    ) -> dict[str, int | float]:
        """
        Get statistics about the root index.
        
        Args:
            root_index: Dictionary mapping root to list of token IDs
            
        Returns:
            Dictionary with statistics
        """
        total_roots = len(root_index)
        total_tokens = sum(len(tokens) for tokens in root_index.values())
        
        if total_roots == 0:
            return {
                "total_roots": 0,
                "total_tokens": 0,
                "avg_tokens_per_root": 0.0,
                "max_tokens_per_root": 0,
                "min_tokens_per_root": 0,
            }
        
        token_counts = [len(tokens) for tokens in root_index.values()]
        
        return {
            "total_roots": total_roots,
            "total_tokens": total_tokens,
            "avg_tokens_per_root": total_tokens / total_roots,
            "max_tokens_per_root": max(token_counts),
            "min_tokens_per_root": min(token_counts),
        }
