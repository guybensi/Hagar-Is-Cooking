from app.database.recipe_history_repository import RecipeHistoryRepository
from app.models.recipe import FinalRecipe
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
