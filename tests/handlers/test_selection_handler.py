from datetime import datetime
from unittest.mock import AsyncMock

from app.database.session_repository import SessionRepository
from app.handlers.selection_handler import handle_recipe_selection
from app.models.recipe import ExtractedRecipe, Ingredient, StructuredRecipe
from app.models.search import SearchResult
from app.models.session import SessionData, SessionState
from app.services.recipe_extraction_service import RecipeExtractionError
from app.services.recipe_structuring_service import RecipeStructuringError
from app.static import labels
from tests.conftest import make_callback_update


def _extracted() -> ExtractedRecipe:
    return ExtractedRecipe(
        source_url="https://www.mako.co.il/food/a",
        title="שניצל",
        raw_text="...",
        fetched_at=datetime.utcnow(),
    )


def _structured() -> StructuredRecipe:
    return StructuredRecipe(
        recipe_name="שניצל עוף",
        ingredients=[Ingredient(name="חזה עוף", amount="500 גרם"), Ingredient(name="ביצה")],
        instructions=["לשטוף", "לטגן"],
    )


async def _seed_awaiting_selection(session_factory, chat_id: int) -> None:
    async with session_factory() as db_session:
        await SessionRepository(db_session).upsert(
            SessionData(
                chat_id=chat_id,
                state=SessionState.AWAITING_RECIPE_SELECTION,
                search_results=[
                    SearchResult(title="שניצל א", url="https://www.mako.co.il/food/a"),
                    SearchResult(title="שניצל ב", url="https://www.mako.co.il/food/b"),
                ],
            )
        )


async def test_stale_selection_when_session_not_awaiting_selection(
    context_with_db, session_factory
):
    update = make_callback_update("select:0", chat_id=1)

    await handle_recipe_selection(update, context_with_db)

    update.callback_query.edit_message_text.assert_awaited_once_with(
        labels.STALE_SELECTION_MESSAGE
    )


async def test_stale_selection_when_index_out_of_range(context_with_db, session_factory):
    update = make_callback_update("select:5", chat_id=2)
    await _seed_awaiting_selection(session_factory, 2)

    await handle_recipe_selection(update, context_with_db)

    update.callback_query.edit_message_text.assert_awaited_once_with(
        labels.STALE_SELECTION_MESSAGE
    )


async def test_successful_selection_shows_checklist_and_advances_session(
    context_with_db, session_factory
):
    update = make_callback_update("select:0", chat_id=3)
    await _seed_awaiting_selection(session_factory, 3)

    extraction_service = AsyncMock()
    extraction_service.extract_recipe.return_value = _extracted()
    context_with_db.bot_data["recipe_extraction_service"] = extraction_service

    structuring_service = AsyncMock()
    structuring_service.structure.return_value = _structured()
    context_with_db.bot_data["recipe_structuring_service"] = structuring_service

    await handle_recipe_selection(update, context_with_db)

    update.callback_query.answer.assert_awaited_once()
    final_call_text = update.callback_query.edit_message_text.call_args_list[-1].args[0]
    assert "שניצל עוף" in final_call_text
    assert "חזה עוף" in final_call_text

    async with session_factory() as db_session:
        session = await SessionRepository(db_session).get_by_chat_id(3)

    assert session.state == SessionState.AWAITING_CHECKLIST
    assert session.selected_index == 0
    assert len(session.checklist) == 2
    assert all(item.checked for item in session.checklist)


async def test_extraction_failure_reverts_session(context_with_db, session_factory):
    update = make_callback_update("select:0", chat_id=4)
    await _seed_awaiting_selection(session_factory, 4)

    extraction_service = AsyncMock()
    extraction_service.extract_recipe.side_effect = RecipeExtractionError("fetch failed")
    context_with_db.bot_data["recipe_extraction_service"] = extraction_service

    await handle_recipe_selection(update, context_with_db)

    update.callback_query.edit_message_text.assert_awaited_with(labels.EXTRACTION_FAILED_MESSAGE)

    async with session_factory() as db_session:
        session = await SessionRepository(db_session).get_by_chat_id(4)

    assert session.state == SessionState.AWAITING_DISH_QUERY


async def test_structuring_failure_reverts_session(context_with_db, session_factory):
    update = make_callback_update("select:0", chat_id=5)
    await _seed_awaiting_selection(session_factory, 5)

    extraction_service = AsyncMock()
    extraction_service.extract_recipe.return_value = _extracted()
    context_with_db.bot_data["recipe_extraction_service"] = extraction_service

    structuring_service = AsyncMock()
    structuring_service.structure.side_effect = RecipeStructuringError("bad json")
    context_with_db.bot_data["recipe_structuring_service"] = structuring_service

    await handle_recipe_selection(update, context_with_db)

    update.callback_query.edit_message_text.assert_awaited_with(labels.STRUCTURING_FAILED_MESSAGE)

    async with session_factory() as db_session:
        session = await SessionRepository(db_session).get_by_chat_id(5)

    assert session.state == SessionState.AWAITING_DISH_QUERY
