from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from app.models.recipe import ExtractedRecipe
from app.utils.logging import get_logger
from app.utils.retry import retry_transient_errors

logger = get_logger(__name__)

MAX_RAW_TEXT_LENGTH = 6000
_NOISE_TAGS = ("script", "style", "nav", "header", "footer", "aside", "iframe", "form", "svg")
_NOISE_KEYWORDS = (
    "banner",
    "ad-",
    "advert",
    "social",
    "comment",
    "related",
    "sponsor",
    "cookie",
    "popup",
    "share",
    "newsletter",
    "breadcrumb",
)
_USER_AGENT = "Mozilla/5.0 (compatible; HagarIsCookingBot/1.0; +https://github.com)"


class RecipeExtractionError(Exception):
    """Raised when fetching or parsing a recipe page fails."""


class RecipeExtractionService:
    """Fetches a mako.co.il recipe page and strips it down to clean body text.

    Deliberately does NOT split the text into ingredients/instructions -- that semantic
    understanding is delegated to the Groq structuring step, since hand-written CSS-selector
    heuristics for that split would be brittle against markup changes.
    """

    @retry_transient_errors(httpx.HTTPError)
    async def _fetch_html(self, url: str) -> str:
        async with httpx.AsyncClient(
            timeout=15, headers={"User-Agent": _USER_AGENT}, follow_redirects=True
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text

    async def extract_recipe(self, url: str) -> ExtractedRecipe:
        try:
            html = await self._fetch_html(url)
        except Exception as exc:
            logger.error("recipe_extraction_fetch_failed", url=url, error=str(exc))
            raise RecipeExtractionError(f"Failed to fetch {url}: {exc}") from exc

        soup = BeautifulSoup(html, "html.parser")

        for tag in soup.find_all(_NOISE_TAGS):
            tag.decompose()

        for element in soup.find_all(True):
            classes_and_id = " ".join([*element.get("class", []), element.get("id") or ""])
            if any(keyword in classes_and_id.lower() for keyword in _NOISE_KEYWORDS):
                element.decompose()

        title_tag = soup.find("h1")
        title = title_tag.get_text(strip=True) if title_tag else None

        main_content = soup.find("article") or soup.body or soup
        raw_text = main_content.get_text(separator="\n", strip=True)[:MAX_RAW_TEXT_LENGTH]

        return ExtractedRecipe(
            source_url=url, title=title, raw_text=raw_text, fetched_at=datetime.utcnow()
        )
