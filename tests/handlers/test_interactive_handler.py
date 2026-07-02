from unittest.mock import AsyncMock

from app.database.session_repository import SessionRepository
from app.handlers.interactive_handler import (
    build_step_keyboard,
    build_step_message,
    handle_step_navigation,
    handle_why,
)
from app.models.recipe import FinalRecipe, Ingredient
from app.models.session import SessionData, SessionState
from app.services.explanation_service import ExplanationError
from app.static import labels
from tests.conftest import make_callback_update


def _final_recipe() -> FinalRecipe:
    return FinalRecipe(
        recipe_name="שניצל עוף מותאם",
        ingredients=[Ingredient(name="חזה עוף")],
        instructions=["לשטוף את החזה", "לטגן עד להזהבה", "להגיש חם"],
    )


async def _seed_interactive(session_factory, chat_id: int, *, step_index: int) -> None:
    async with session_factory() as db_session:
        await SessionRepository(db_session).upsert(
            SessionData(
                chat_id=chat_id,
                state=SessionState.DELIVERING_INTERACTIVE,
                final_recipe=_final_recipe(),
                current_step_index=step_index,
            )
        )


async def test_done_advances_to_next_step(context_with_db, session_factory):
    update = make_callback_update("step:done", chat_id=1)
    await _seed_interactive(session_factory, 1, step_index=0)

    await handle_step_navigation(update, context_with_db)

    message = update.callback_query.edit_message_text.call_args.args[0]
    assert "שלב 2 מתוך 3" in message
    assert "לטגן עד להזהבה" in message

    async with session_factory() as db_session:
        session = await SessionRepository(db_session).get_by_chat_id(1)

    assert session.current_step_index == 1
    assert session.state == SessionState.DELIVERING_INTERACTIVE


async def test_prev_goes_back_a_step(context_with_db, session_factory):
    update = make_callback_update("step:prev", chat_id=2)
    await _seed_interactive(session_factory, 2, step_index=1)

    await handle_step_navigation(update, context_with_db)

    message = update.callback_query.edit_message_text.call_args.args[0]
    assert "שלב 1 מתוך 3" in message

    async with session_factory() as db_session:
        session = await SessionRepository(db_session).get_by_chat_id(2)

    assert session.current_step_index == 0


async def test_prev_on_first_step_stays_on_first_step(context_with_db, session_factory):
    update = make_callback_update("step:prev", chat_id=3)
    await _seed_interactive(session_factory, 3, step_index=0)

    await handle_step_navigation(update, context_with_db)

    async with session_factory() as db_session:
        session = await SessionRepository(db_session).get_by_chat_id(3)

    assert session.current_step_index == 0


def test_first_step_has_no_previous_button():
    session = SessionData(chat_id=1, final_recipe=_final_recipe(), current_step_index=0)
    keyboard = build_step_keyboard(session)
    buttons = [button.text for row in keyboard.inline_keyboard for button in row]

    assert labels.PREVIOUS_STEP_BUTTON not in buttons


async def test_done_on_last_step_completes_cooking(context_with_db, session_factory):
    update = make_callback_update("step:done", chat_id=5)
    await _seed_interactive(session_factory, 5, step_index=2)

    await handle_step_navigation(update, context_with_db)

    update.callback_query.edit_message_text.assert_awaited_once_with(
        labels.COOKING_COMPLETE_MESSAGE.format(recipe_name="שניצל עוף מותאם")
    )

    async with session_factory() as db_session:
        session = await SessionRepository(db_session).get_by_chat_id(5)

    assert session.state == SessionState.COMPLETED


async def test_rejects_when_not_delivering_interactive(context_with_db, session_factory):
    update = make_callback_update("step:done", chat_id=6)
    # No session seeded -> defaults to IDLE.

    await handle_step_navigation(update, context_with_db)

    update.callback_query.edit_message_text.assert_awaited_once_with(
        labels.STALE_SELECTION_MESSAGE
    )


def test_build_step_message_formats_header_and_text():
    session = SessionData(
        chat_id=1,
        final_recipe=_final_recipe(),
        current_step_index=1,
    )
    message = build_step_message(session)

    assert "שלב 2 מתוך 3" in message
    assert "לטגן עד להזהבה" in message


def test_build_step_keyboard_shows_finish_label_on_last_step():
    session = SessionData(chat_id=1, final_recipe=_final_recipe(), current_step_index=2)
    keyboard = build_step_keyboard(session)
    buttons = [button.text for row in keyboard.inline_keyboard for button in row]

    assert labels.FINISH_COOKING_BUTTON in buttons
    assert labels.DONE_STEP_BUTTON not in buttons


def test_build_step_keyboard_always_includes_why_button():
    session = SessionData(chat_id=1, final_recipe=_final_recipe(), current_step_index=0)
    keyboard = build_step_keyboard(session)
    buttons = [button.callback_data for row in keyboard.inline_keyboard for button in row]

    assert "step:why" in buttons


async def test_why_answers_with_explanation_alert_and_does_not_change_state(
    context_with_db, session_factory
):
    update = make_callback_update("step:why", chat_id=7)
    await _seed_interactive(session_factory, 7, step_index=1)

    explanation_service = AsyncMock()
    explanation_service.explain.return_value = "כדי לשמור על העסיסיות של הבשר."
    context_with_db.bot_data["explanation_service"] = explanation_service

    await handle_why(update, context_with_db)

    update.callback_query.answer.assert_awaited_once_with(
        "כדי לשמור על העסיסיות של הבשר.", show_alert=True
    )
    explanation_service.explain.assert_awaited_once()

    async with session_factory() as db_session:
        session = await SessionRepository(db_session).get_by_chat_id(7)

    assert session.current_step_index == 1
    assert session.state == SessionState.DELIVERING_INTERACTIVE


async def test_why_truncates_long_explanations_for_the_alert_limit(
    context_with_db, session_factory
):
    update = make_callback_update("step:why", chat_id=8)
    await _seed_interactive(session_factory, 8, step_index=0)

    explanation_service = AsyncMock()
    explanation_service.explain.return_value = "א" * 300
    context_with_db.bot_data["explanation_service"] = explanation_service

    await handle_why(update, context_with_db)

    alert_text = update.callback_query.answer.call_args.args[0]
    assert len(alert_text) <= 200


async def test_why_shows_failure_alert_on_explanation_error(context_with_db, session_factory):
    update = make_callback_update("step:why", chat_id=9)
    await _seed_interactive(session_factory, 9, step_index=0)

    explanation_service = AsyncMock()
    explanation_service.explain.side_effect = ExplanationError("boom")
    context_with_db.bot_data["explanation_service"] = explanation_service

    await handle_why(update, context_with_db)

    update.callback_query.answer.assert_awaited_once_with(
        labels.EXPLANATION_FAILED_MESSAGE, show_alert=True
    )


async def test_why_rejects_when_not_delivering_interactive(context_with_db, session_factory):
    update = make_callback_update("step:why", chat_id=10)
    # No session seeded -> defaults to IDLE.

    await handle_why(update, context_with_db)

    update.callback_query.answer.assert_awaited_once_with(
        labels.STALE_SELECTION_MESSAGE, show_alert=True
    )
