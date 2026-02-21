"""
MultiSourceVerifier — consensus algorithm for root verification.

Runs all extractors, collects their results, and selects the root
with the highest weighted agreement score.

Features:
    - Query multiple extractors in parallel
    - Weighted trust scores (cache/corpus > algorithmic)
    - Confidence scoring based on agreement + source trustworthiness
    - Disk-backed cache for verified results
    - Conflict logging for auditability
"""
import asyncio
import json
from pathlib import Path
from typing import Optional

from backend.services.extractors.base import (
    RootExtractionResult,
    RootExtractor,
    VerifiedRoot,
)


class MultiSourceVerifier:
    """
    Verify roots across multiple sources with consensus algorithm.
    """

    # Trust weights for different source types
    SOURCE_WEIGHTS: dict[str, float] = {
        'offline_corpus_cache': 10.0,   # Highest trust: pre-verified corpus data
        'qurancorpus': 10.0,            # Highest trust: authoritative online corpus
        'pyarabic': 5.0,                # Medium-high trust: database + algorithm
        'alkhalil': 3.0,                # Medium trust: algorithmic only
    }

    def __init__(
        self,
        extractors: list[RootExtractor],
        cache_path: Optional[Path] = None,
    ) -> None:
        self.extractors = extractors
        self.cache_path = cache_path
        self.cache: dict[str, VerifiedRoot] = {}

        if cache_path and cache_path.exists():
            self._load_cache()

    # ── Cache persistence ─────────────────────────────────────────

    def _load_cache(self) -> None:
        """Load cached verified roots."""
        try:
            with open(self.cache_path, 'r', encoding='utf-8') as f:  # type: ignore[arg-type]
                data: dict = json.load(f)

                for word, info in data.items():
                    self.cache[word] = VerifiedRoot(
                        word=word,
                        root=info['root'],
                        sources=info['sources'],
                        confidence=info['confidence'],
                        agreement_count=info['agreement_count'],
                        total_sources=info['total_sources'],
                    )

                print(f"[MultiSourceVerifier] Loaded {len(self.cache)} cached roots")
        except Exception as e:
            print(f"[MultiSourceVerifier] Failed to load cache: {e}")

    def _save_cache(self) -> None:
        """Save verified roots to cache."""
        try:
            if self.cache_path:
                self.cache_path.parent.mkdir(parents=True, exist_ok=True)

                data: dict = {}
                for word, verified in self.cache.items():
                    data[word] = {
                        'root': verified.root,
                        'sources': verified.sources,
                        'confidence': verified.confidence,
                        'agreement_count': verified.agreement_count,
                        'total_sources': verified.total_sources,
                    }

                with open(self.cache_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                print(f"[MultiSourceVerifier] Saved {len(self.cache)} roots to cache")
        except Exception as e:
            print(f"[MultiSourceVerifier] Failed to save cache: {e}")

    def save_cache(self) -> None:
        """Public method to save cache."""
        self._save_cache()

    async def close(self) -> None:
        """Close all extractors (no-op for stateless extractors)."""
        pass

    # ── Verification ──────────────────────────────────────────────

    async def verify_root(
        self,
        word: str,
        max_retries: int = 3,
    ) -> Optional[VerifiedRoot]:
        """
        Verify root across multiple sources with retry logic.

        Returns VerifiedRoot with consensus, or None if all extractors fail.
        """
        if word in self.cache:
            print(f"[MultiSourceVerifier] Cache hit for: {word}")
            return self.cache[word]

        print(f"[MultiSourceVerifier] Verifying root for: {word}")

        all_results: list[RootExtractionResult] = []

        for extractor in self.extractors:
            for attempt in range(max_retries):
                try:
                    result = await extractor.extract_root(word)
                    if result.success:
                        all_results.append(result)
                        break
                    elif attempt < max_retries - 1:
                        print(f"[{extractor.name}] Attempt {attempt + 1} failed: {result.error}, retrying...")
                        await asyncio.sleep(2 ** attempt)
                    else:
                        print(f"[{extractor.name}] All attempts failed for: {word}")
                        all_results.append(result)
                except Exception as e:
                    print(f"[{extractor.name}] Exception on attempt {attempt + 1}: {e}")
                    if attempt == max_retries - 1:
                        all_results.append(RootExtractionResult(
                            word=word,
                            root=None,
                            source=extractor.name,
                            success=False,
                            error=str(e),
                        ))

        # Filter successful results
        successful = [r for r in all_results if r.success and r.root]
        if not successful:
            print(f"[MultiSourceVerifier] No successful extractions for: {word}")
            return None

        # Calculate weighted consensus
        root_weighted_votes: dict[str, float] = {}
        root_simple_votes: dict[str, int] = {}

        for result in successful:
            root = result.root  # type: ignore[assignment]
            weight = self.SOURCE_WEIGHTS.get(result.source, 1.0)
            root_weighted_votes[root] = root_weighted_votes.get(root, 0.0) + weight
            root_simple_votes[root] = root_simple_votes.get(root, 0) + 1

        # Select root with highest weighted score
        most_common_root: str = max(root_weighted_votes, key=root_weighted_votes.get)  # type: ignore[arg-type]
        weighted_score = root_weighted_votes[most_common_root]
        simple_vote_count = root_simple_votes[most_common_root]

        sources: dict[str, str] = {r.source: r.root for r in successful}  # type: ignore[misc]

        total_sources = len(successful)
        total_weight = sum(root_weighted_votes.values())

        weight_confidence = weighted_score / total_weight if total_weight > 0 else 0.5

        agreement_boost = 0.0
        if simple_vote_count >= 3:
            agreement_boost = 0.2
        elif simple_vote_count == 2:
            agreement_boost = 0.1

        confidence = min(1.0, weight_confidence + agreement_boost)

        # Ensure minimum confidence for high-trust sources
        if any(
            r.source in ('offline_corpus_cache', 'qurancorpus') and r.root == most_common_root
            for r in successful
        ):
            confidence = max(confidence, 0.95)

        verified = VerifiedRoot(
            word=word,
            root=most_common_root,
            sources=sources,
            confidence=confidence,
            agreement_count=simple_vote_count,
            total_sources=total_sources,
        )

        self.cache[word] = verified

        print(
            f"[MultiSourceVerifier] Verified: {word} -> {most_common_root} "
            f"(confidence: {confidence:.2f}, agreement: {simple_vote_count}/{total_sources}, "
            f"weighted: {weighted_score:.1f}/{total_weight:.1f})"
        )

        if len(root_weighted_votes) > 1:
            conflicts = [f"{root}({votes:.1f})" for root, votes in root_weighted_votes.items()]
            print(f"[MultiSourceVerifier] Conflicts: {', '.join(conflicts)}")

        return verified
