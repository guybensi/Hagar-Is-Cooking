from unittest.mock import AsyncMock

from app.models.recipe import FinalRecipe, Ingredient
from app.models.session import SessionData
from app.services.recipe_history_service import RecipeHistoryService


def _recipe() -> FinalRecipe:
    return FinalRecipe(
        recipe_name="שניצל עוף", ingredients=[Ingredient(name="חזה עוף")], instructions=["לטגן"]
    )


async def test_log_completed_delegates_to_repository():
    repository = AsyncMock()
    service = RecipeHistoryService(repository)
    recipe = _recipe()

    await service.log_completed(123, recipe, "https://www.mako.co.il/food/a", "full")

    repository.add.assert_awaited_once_with(
        123, recipe, "https://www.mako.co.il/food/a", "full"
    )


async def test_log_completed_once_logs_and_marks_session():
    repository = AsyncMock()
    service = RecipeHistoryService(repository)
    session = SessionData(chat_id=1, final_recipe=_recipe(), history_logged=False)

    await service.log_completed_once(session, 123, "full")

    repository.add.assert_awaited_once()
    assert session.history_logged is True


async def test_log_completed_once_is_a_no_op_when_already_logged():
    repository = AsyncMock()
    service = RecipeHistoryService(repository)
    session = SessionData(chat_id=1, final_recipe=_recipe(), history_logged=True)

    await service.log_completed_once(session, 123, "full")

    repository.add.assert_not_awaited()


async def test_log_completed_once_is_a_no_op_without_a_final_recipe():
    repository = AsyncMock()
    service = RecipeHistoryService(repository)
    session = SessionData(chat_id=1, final_recipe=None, history_logged=False)

    await service.log_completed_once(session, 123, "full")

    repository.add.assert_not_awaited()
