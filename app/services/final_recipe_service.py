from app.models.recipe import FinalRecipe, Ingredient, StructuredRecipe
from app.models.substitution import SubstitutionDecision
from app.services.llm.groq_client import GroqClient, LLMStructuringError
from app.utils.logging import get_logger

logger = get_logger(__name__)


class FinalRecipeGenerationError(Exception):
    """Raised when Groq fails to generate the final, ingredient-adapted recipe."""


class FinalRecipeService:
    def __init__(self, groq_client: GroqClient) -> None:
        self._groq_client = groq_client

    async def generate(
        self,
        structured: StructuredRecipe,
        available: list[Ingredient],
        missing: list[Ingredient],
        accepted_substitutions: list[SubstitutionDecision],
    ) -> FinalRecipe:
        try:
            return await self._groq_client.rewrite_final_recipe(
                structured, available, missing, accepted_substitutions
            )
        except LLMStructuringError as exc:
            logger.error(
                "final_recipe_generation_failed", recipe=structured.recipe_name, error=str(exc)
            )
            raise FinalRecipeGenerationError(str(exc)) from exc
