from app.models.recipe import FinalRecipe
from app.services.llm.groq_client import GroqClient, LLMStructuringError
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ExplanationError(Exception):
    """Raised when Groq fails to explain why a cooking step matters."""


class ExplanationService:
    def __init__(self, groq_client: GroqClient) -> None:
        self._groq_client = groq_client

    async def explain(self, recipe: FinalRecipe, step_index: int) -> str:
        try:
            return await self._groq_client.explain_step(recipe, step_index)
        except LLMStructuringError as exc:
            logger.error(
                "step_explanation_failed",
                recipe=recipe.recipe_name,
                step_index=step_index,
                error=str(exc),
            )
            raise ExplanationError(str(exc)) from exc
