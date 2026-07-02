import asyncio
from datetime import datetime

from tavily import TavilyClient

from app.models.recipe import ExtractedRecipe
from app.utils.logging import get_logger

logger = get_logger(__name__)

MAX_RAW_TEXT_LENGTH = 6000


class RecipeExtractionError(Exception):
    """Raised when Tavily fails to extract a recipe page."""


class RecipeExtractionService:
    def __init__(self, api_key: str) -> None:
        self._client = TavilyClient(api_key=api_key)

    async def extract_recipe(self, url: str) -> ExtractedRecipe:
        try:
            response = await asyncio.to_thread(
                self._client.extract, urls=url, format="text"
            )
        except Exception as exc:
            logger.error("recipe_extraction_failed", url=url, error=str(exc))
            raise RecipeExtractionError(f"Tavily extract failed for {url}: {exc}") from exc

        results = response.get("results", [])
        if not results:
            failed = response.get("failed_results", [])
            reason = failed[0].get("error", "unknown") if failed else "no results returned"
            logger.error("recipe_extraction_no_results", url=url, reason=reason)
            raise RecipeExtractionError(f"Tavily could not extract {url}: {reason}")

        hit = results[0]
        raw_text = (hit.get("raw_content") or "")[:MAX_RAW_TEXT_LENGTH]
        title = hit.get("title") or None

        return ExtractedRecipe(
            source_url=url,
            title=title,
            raw_text=raw_text,
            fetched_at=datetime.utcnow(),
        )
