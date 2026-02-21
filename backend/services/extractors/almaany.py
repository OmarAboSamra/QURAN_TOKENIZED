"""
AlMaanyExtractor — scrapes roots from almaany.com Arabic dictionary.

AlMaany is a comprehensive Arabic-Arabic dictionary that provides
word roots, definitions, and morphological information.
"""
import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from backend.services.extractors.base import RootExtractionResult, RootExtractor


class AlMaanyExtractor(RootExtractor):
    """Extract roots from AlMaany Arabic Dictionary (almaany.com)."""

    def __init__(self) -> None:
        super().__init__("almaany")
        self.base_url = "https://www.almaany.com/ar/dict/ar-ar"
        self.min_request_interval = 1.5

    def _create_client(self) -> httpx.AsyncClient:
        """Create a new HTTP client."""
        return httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "ar,en-US;q=0.7,en;q=0.3",
                "Referer": "https://www.almaany.com/",
            },
        )

    async def extract_root(self, word: str, **kwargs) -> RootExtractionResult:
        """Extract root from AlMaany dictionary."""
        client: Optional[httpx.AsyncClient] = None
        try:
            await self.rate_limit()
            client = self._create_client()
            url = f"{self.base_url}/{word}/"

            print(f"[{self.name}] Fetching: {word}")

            response = await client.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            root_found: Optional[str] = None

            # Strategy 1: Look for "الجذر" (root) label
            for text_elem in soup.find_all(string=re.compile(r'الجذر')):
                parent = text_elem.parent
                if parent:
                    next_elem = parent.find_next_sibling()
                    if next_elem:
                        root_text = next_elem.get_text(strip=True)
                        root_match = re.search(r'[\u0621-\u064A]+', root_text)
                        if root_match:
                            root_found = root_match.group(0)
                            break

            # Strategy 2: Look in definition section for root patterns
            if not root_found:
                for elem in soup.find_all(['div', 'span', 'p']):
                    text = elem.get_text()
                    root_pattern = re.search(
                        r'(?:الجذر|الأصل|جذر)[\s:]+([ا-ي]{3,4})', text,
                    )
                    if root_pattern:
                        root_found = root_pattern.group(1)
                        break

            if root_found:
                print(f"[{self.name}] Found root: {word} -> {root_found}")
                return RootExtractionResult(
                    word=word,
                    root=root_found,
                    source=self.name,
                    success=True,
                    confidence=0.85,
                )
            else:
                return RootExtractionResult(
                    word=word,
                    root=None,
                    source=self.name,
                    success=False,
                    error="Root not found in dictionary",
                )

        except httpx.HTTPError as e:
            return RootExtractionResult(
                word=word,
                root=None,
                source=self.name,
                success=False,
                error=f"HTTP error: {e}",
            )
        except Exception as e:
            return RootExtractionResult(
                word=word,
                root=None,
                source=self.name,
                success=False,
                error=f"Error: {e}",
            )
        finally:
            if client:
                await client.aclose()
