"""
BahethExtractor — scrapes roots from baheth.info Arabic dictionary.

Baheth is an Arabic-Arabic dictionary that provides morphological
analysis and root information.
"""
import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from backend.services.extractors.base import RootExtractionResult, RootExtractor


class BahethExtractor(RootExtractor):
    """Extract roots from Baheth Arabic Dictionary (baheth.info)."""

    def __init__(self) -> None:
        super().__init__("baheth")
        self.base_url = "https://www.baheth.info"
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
            },
        )

    async def extract_root(self, word: str, **kwargs) -> RootExtractionResult:
        """Extract root from Baheth dictionary."""
        client: Optional[httpx.AsyncClient] = None
        try:
            await self.rate_limit()
            client = self._create_client()
            url = f"{self.base_url}/all.jsp"
            params = {"term": word}

            print(f"[{self.name}] Searching: {word}")

            response = await client.get(url, params=params)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            root_found: Optional[str] = None

            for cell in soup.find_all(['td', 'div', 'span']):
                text = cell.get_text(strip=True)
                if 'الجذر' in text or 'جذر' in text:
                    root_match = re.search(r'الجذر[\s:]*([ا-ي]{3,4})', text)
                    if root_match:
                        root_found = root_match.group(1)
                        break

                    next_elem = cell.find_next_sibling()
                    if next_elem:
                        next_text = next_elem.get_text(strip=True)
                        root_match = re.search(r'([ا-ي]{3,4})', next_text)
                        if root_match:
                            root_found = root_match.group(1)
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
                    error="Root not found",
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
