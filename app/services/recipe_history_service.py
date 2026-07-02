from app.database.recipe_history_repository import RecipeHistoryRepository
from app.models.recipe import FinalRecipe
from app.models.session import SessionData
from app.utils.logging import get_logger

logger = get_logger(__name__)


class RecipeHistoryService:
    def __init__(self, repository: RecipeHistoryRepository) -> None:
        self._repository = repository

    async def log_completed(
        self,
        telegram_user_id: int,
        final_recipe: FinalRecipe,
        source_url: str | None,
        delivery_mode: str,
    ) -> None:
        await self._repository.add(telegram_user_id, final_recipe, source_url, delivery_mode)
        logger.info(
            "recipe_completed",
            telegram_user_id=telegram_user_id,
            recipe=final_recipe.recipe_name,
            delivery_mode=delivery_mode,
        )

    async def log_completed_once(
        self, session: SessionData, telegram_user_id: int, delivery_mode: str
    ) -> None:
        """Logs at most once per session.

        Users can freely toggle between full and interactive delivery mode, and both paths can
        reach COMPLETED (full immediately, interactive after the last step) -- this guards
        against logging the same cooking session to recipe_history twice.
        """
        if session.history_logged or session.final_recipe is None:
            return

        source_url = session.extracted_recipe.source_url if session.extracted_recipe else None
        await self.log_completed(telegram_user_id, session.final_recipe, source_url, delivery_mode)
        session.history_logged = True
