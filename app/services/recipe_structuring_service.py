from app.models.recipe import ExtractedRecipe, StructuredRecipe
from app.services.llm.groq_client import GroqClient, LLMStructuringError
from app.utils.logging import get_logger

logger = get_logger(__name__)


class RecipeStructuringError(Exception):
    """Raised when Groq fails to structure a scraped recipe."""


class RecipeStructuringService:
    def __init__(self, groq_client: GroqClient) -> None:
        self._groq_client = groq_client

    async def structure(self, extracted: ExtractedRecipe) -> StructuredRecipe:
        try:
            return await self._groq_client.structure_recipe(extracted)
        except LLMStructuringError as exc:
            logger.error("recipe_structuring_failed", url=extracted.source_url, error=str(exc))
            raise RecipeStructuringError(str(exc)) from exc
