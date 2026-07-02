from app.models.recipe import Ingredient, StructuredRecipe
from app.models.substitution import SubstitutionDecision
from app.services.llm.groq_client import GroqClient, LLMStructuringError
from app.utils.logging import get_logger

logger = get_logger(__name__)


class SubstitutionDecisionError(Exception):
    """Raised when Groq fails to decide on missing-ingredient substitutions."""


class SubstitutionService:
    def __init__(self, groq_client: GroqClient) -> None:
        self._groq_client = groq_client

    async def decide(
        self, missing_ingredients: list[Ingredient], recipe: StructuredRecipe
    ) -> list[SubstitutionDecision]:
        try:
            return await self._groq_client.decide_substitutions(missing_ingredients, recipe)
        except LLMStructuringError as exc:
            logger.error(
                "substitution_decision_failed", recipe=recipe.recipe_name, error=str(exc)
            )
            raise SubstitutionDecisionError(str(exc)) from exc
