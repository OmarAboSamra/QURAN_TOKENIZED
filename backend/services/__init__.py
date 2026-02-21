"""
Services package — business logic layer.

Contains the core analysis pipeline:
    TokenizerService      – splits raw text into word tokens
    RootExtractionService – queries multiple sources for Arabic roots
    DiscrepancyChecker    – reconciles conflicting root results
    ReferenceLinker       – builds cross-references between related tokens

Sub-packages:
    extractors/           – individual root-extraction backends (C4 refactor)
"""
from backend.services.discrepancy_checker import DiscrepancyChecker, DiscrepancyReport
from backend.services.reference_linker import ReferenceLinker
from backend.services.root_extraction_service import RootExtractionService
from backend.services.extractors.base import RootExtractionResult
from backend.services.tokenizer_service import TokenizerService, WordToken

__all__ = [
    "TokenizerService",
    "WordToken",
    "RootExtractionService",
    "RootExtractionResult",
    "DiscrepancyChecker",
    "DiscrepancyReport",
    "ReferenceLinker",
]
