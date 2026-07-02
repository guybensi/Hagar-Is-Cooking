import asyncio
from urllib.parse import urlparse

import httpx
from tavily import TavilyClient

from app.models.search import SearchResult
from app.utils.logging import get_logger
from app.utils.retry import retry_transient_errors

logger = get_logger(__name__)

MAKO_DOMAIN = "mako.co.il"
MAX_RESULTS = 3


class RecipeSearchError(Exception):
    """Raised when Tavily search fails after retries."""


class RecipeSearchService:
    """Searches mako.co.il recipes via Tavily's site-restricted web search."""

    def __init__(self, api_key: str) -> None:
        self._client = TavilyClient(api_key=api_key)

    @retry_transient_errors(httpx.HTTPError, ConnectionError)
    async def _search(self, query: str) -> dict:
        return await asyncio.to_thread(
            self._client.search, query=query, max_results=MAX_RESULTS
        )

    async def search_recipes(self, dish_query: str) -> list[SearchResult]:
        query = f"site:{MAKO_DOMAIN} {dish_query}"

        try:
            raw_response = await self._search(query)
        except Exception as exc:
            logger.error("recipe_search_failed", query=query, error=str(exc))
            raise RecipeSearchError(f"Tavily search failed for query {query!r}: {exc}") from exc

        results: list[SearchResult] = []
        for hit in raw_response.get("results", []):
            url = hit.get("url", "")
            if MAKO_DOMAIN not in urlparse(url).netloc:
                continue
            results.append(
                SearchResult(title=hit.get("title", ""), url=url, snippet=hit.get("content"))
            )

        return results[:MAX_RESULTS]
