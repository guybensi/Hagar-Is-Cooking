from unittest.mock import AsyncMock, MagicMock

from app.database.session_repository import SessionRepository
from app.handlers.search_handler import handle_free_text
from app.models.search import SearchResult
from app.models.session import SessionData, SessionState
from app.static import labels
from tests.conftest import make_update


def _attach_loading_message(update) -> MagicMock:
    loading_message = MagicMock()
    loading_message.edit_text = AsyncMock()
    update.message.reply_text = AsyncMock(return_value=loading_message)
    return loading_message


async def test_nudges_user_when_mid_flow(context_with_db, session_factory):
    update = make_update(text="פסטה", chat_id=1)
    async with session_factory() as db_session:
        await SessionRepository(db_session).upsert(
            SessionData(chat_id=1, state=SessionState.AWAITING_CHECKLIST)
        )

    await handle_free_text(update, context_with_db)

    update.message.reply_text.assert_awaited_once_with(labels.AWAITING_QUERY_NUDGE)


async def test_empty_text_prompts_for_a_dish(context_with_db):
    update = make_update(text="   ", chat_id=2)

    await handle_free_text(update, context_with_db)

    update.message.reply_text.assert_awaited_once_with(labels.EMPTY_QUERY_MESSAGE)


async def test_successful_search_shows_results_and_advances_session(
    context_with_db, session_factory
):
    update = make_update(text="שניצל", chat_id=3)
    loading_message = _attach_loading_message(update)

    groq_client = AsyncMock()
    groq_client.normalize_dish_query.return_value = "שניצל"
    context_with_db.bot_data["groq_client"] = groq_client

    recipe_search_service = AsyncMock()
    recipe_search_service.search_recipes.return_value = [
        SearchResult(title="שניצל קלאסי", url="https://www.mako.co.il/food/a"),
        SearchResult(title="שניצל בתנור", url="https://www.mako.co.il/food/b"),
    ]
    context_with_db.bot_data["recipe_search_service"] = recipe_search_service

    await handle_free_text(update, context_with_db)

    loading_message.edit_text.assert_awaited_once()
    args, kwargs = loading_message.edit_text.call_args
    assert "שניצל קלאסי" in args[0]
    assert kwargs["reply_markup"] is not None

    async with session_factory() as db_session:
        session = await SessionRepository(db_session).get_by_chat_id(3)

    assert session.state == SessionState.AWAITING_RECIPE_SELECTION
    assert len(session.search_results) == 2


async def test_no_results_reverts_session_to_awaiting_dish_query(
    context_with_db, session_factory
):
    update = make_update(text="מנה נדירה", chat_id=4)
    loading_message = _attach_loading_message(update)

    groq_client = AsyncMock()
    groq_client.normalize_dish_query.return_value = "מנה נדירה"
    context_with_db.bot_data["groq_client"] = groq_client

    recipe_search_service = AsyncMock()
    recipe_search_service.search_recipes.return_value = []
    context_with_db.bot_data["recipe_search_service"] = recipe_search_service

    await handle_free_text(update, context_with_db)

    loading_message.edit_text.assert_awaited_once_with(labels.NO_RESULTS_MESSAGE)

    async with session_factory() as db_session:
        session = await SessionRepository(db_session).get_by_chat_id(4)

    assert session.state == SessionState.AWAITING_DISH_QUERY


async def test_search_failure_shows_error_and_resets_session(context_with_db, session_factory):
    update = make_update(text="שניצל", chat_id=5)
    loading_message = _attach_loading_message(update)

    groq_client = AsyncMock()
    groq_client.normalize_dish_query.return_value = "שניצל"
    context_with_db.bot_data["groq_client"] = groq_client

    recipe_search_service = AsyncMock()
    recipe_search_service.search_recipes.side_effect = RuntimeError("Tavily down")
    context_with_db.bot_data["recipe_search_service"] = recipe_search_service

    await handle_free_text(update, context_with_db)

    loading_message.edit_text.assert_awaited_once_with(labels.SEARCH_FAILED_MESSAGE)

    async with session_factory() as db_session:
        session = await SessionRepository(db_session).get_by_chat_id(5)

    assert session.state == SessionState.IDLE


async def test_normalize_failure_falls_back_to_raw_text(context_with_db):
    update = make_update(text="בא לי שניצל", chat_id=6)
    _attach_loading_message(update)

    groq_client = AsyncMock()
    groq_client.normalize_dish_query.side_effect = RuntimeError("groq down")
    context_with_db.bot_data["groq_client"] = groq_client

    recipe_search_service = AsyncMock()
    recipe_search_service.search_recipes.return_value = [
        SearchResult(title="שניצל", url="https://www.mako.co.il/food/a")
    ]
    context_with_db.bot_data["recipe_search_service"] = recipe_search_service

    await handle_free_text(update, context_with_db)

    recipe_search_service.search_recipes.assert_awaited_once_with("בא לי שניצל")
