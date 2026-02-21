"""
Service for detecting and reconciling discrepancies in root extraction.

When multiple sources (qurancorpus, almaany, baheth, etc.) each return a
root for the same word, they may disagree. This service:

    1. Compares all source results for a given word
    2. Calculates a consensus root (most-voted)
    3. Computes a confidence score (fraction of agreeing sources)
    4. Recommends a TokenStatus:
         VERIFIED       – ≥2 sources agree unanimously
         DISCREPANCY    – sources disagree but a majority exists (≥50%)
         MANUAL_REVIEW  – no clear majority (<50% agreement)
         MISSING        – no source returned any root
"""
from collections import Counter
from dataclasses import dataclass
from typing import Optional

from backend.models import TokenStatus


@dataclass
class DiscrepancyReport:
    """Report of discrepancies found in root extraction."""

    word: str
    sources: dict[str, Optional[str]]
    consensus_root: Optional[str]
    has_discrepancy: bool
    confidence: float
    recommended_status: str


class DiscrepancyChecker:
    """
    Service for detecting discrepancies in root extraction results.
    
    This service:
    - Compares roots from multiple sources
    - Detects conflicts and inconsistencies
    - Determines consensus when possible
    - Flags items for manual review
    """

    def __init__(self, min_sources_for_verification: int = 2) -> None:
        """
        Initialize discrepancy checker.
        
        Args:
            min_sources_for_verification: Minimum number of agreeing sources
                                          to consider a root verified
        """
        self.min_sources_for_verification = min_sources_for_verification

    def check_discrepancy(
        self,
        word: str,
        sources: dict[str, Optional[str]],
    ) -> DiscrepancyReport:
        """
        Check for discrepancies in root extraction results.
        
        Args:
            word: The Arabic word being analyzed
            sources: Dictionary mapping source name to extracted root
            
        Returns:
            DiscrepancyReport with analysis results
        """
        # Filter out None values
        valid_roots = {
            source: root for source, root in sources.items() if root is not None
        }
        
        if not valid_roots:
            # No roots extracted
            return DiscrepancyReport(
                word=word,
                sources=sources,
                consensus_root=None,
                has_discrepancy=False,
                confidence=0.0,
                recommended_status=TokenStatus.MISSING.value,
            )
        
        # Count occurrences of each root
        root_counts = Counter(valid_roots.values())
        most_common_root, count = root_counts.most_common(1)[0]
        
        # Check if there's unanimous agreement
        all_agree = len(root_counts) == 1
        
        # Calculate confidence (percentage of sources agreeing)
        total_sources = len(valid_roots)
        confidence = count / total_sources if total_sources > 0 else 0.0
        
        # Determine if there's a discrepancy
        has_discrepancy = not all_agree
        
        # Determine recommended status
        if all_agree and count >= self.min_sources_for_verification:
            status = TokenStatus.VERIFIED.value
        elif has_discrepancy and confidence < 0.5:
            status = TokenStatus.MANUAL_REVIEW.value
        elif has_discrepancy:
            status = TokenStatus.DISCREPANCY.value
        else:
            status = TokenStatus.VERIFIED.value
        
        return DiscrepancyReport(
            word=word,
            sources=sources,
            consensus_root=most_common_root,
            has_discrepancy=has_discrepancy,
            confidence=confidence,
            recommended_status=status,
        )

    def analyze_batch(
        self,
        results: dict[str, dict[str, Optional[str]]],
    ) -> dict[str, DiscrepancyReport]:
        """
        Analyze a batch of extraction results.
        
        Args:
            results: Dictionary mapping word to source results
            
        Returns:
            Dictionary mapping word to discrepancy report
        """
        reports = {}
        
        for word, sources in results.items():
            reports[word] = self.check_discrepancy(word, sources)
        
        return reports

    def get_statistics(
        self,
        reports: dict[str, DiscrepancyReport],
    ) -> dict[str, int]:
        """
        Get statistics from a batch of discrepancy reports.
        
        Args:
            reports: Dictionary of discrepancy reports
            
        Returns:
            Dictionary with statistics
        """
        stats = {
            "total": len(reports),
            "verified": 0,
            "discrepancy": 0,
            "manual_review": 0,
            "missing": 0,
        }
        
        for report in reports.values():
            status = report.recommended_status
            if status == TokenStatus.VERIFIED.value:
                stats["verified"] += 1
            elif status == TokenStatus.DISCREPANCY.value:
                stats["discrepancy"] += 1
            elif status == TokenStatus.MANUAL_REVIEW.value:
                stats["manual_review"] += 1
            elif status == TokenStatus.MISSING.value:
                stats["missing"] += 1
        
        return stats
