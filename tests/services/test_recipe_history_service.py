from unittest.mock import AsyncMock

from app.models.recipe import FinalRecipe, Ingredient
from app.services.recipe_history_service import RecipeHistoryService


async def test_log_completed_delegates_to_repository():
    repository = AsyncMock()
    service = RecipeHistoryService(repository)
    recipe = FinalRecipe(
        recipe_name="שניצל עוף", ingredients=[Ingredient(name="חזה עוף")], instructions=["לטגן"]
    )

    await service.log_completed(123, recipe, "https://www.mako.co.il/food/a", "full")

    repository.add.assert_awaited_once_with(
        123, recipe, "https://www.mako.co.il/food/a", "full"
    )
