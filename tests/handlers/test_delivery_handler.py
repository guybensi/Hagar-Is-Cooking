from app.database.recipe_history_repository import RecipeHistoryRepository
from app.database.session_repository import SessionRepository
from app.handlers.delivery_handler import (
    build_delivery_mode_keyboard,
    build_full_recipe_keyboard,
    build_full_recipe_message,
    handle_mode_choice,
)
from app.models.recipe import FinalRecipe, Ingredient
from app.models.session import SessionData, SessionState
from app.static import labels
from tests.conftest import make_callback_update


def _final_recipe() -> FinalRecipe:
    return FinalRecipe(
        recipe_name="שניצל עוף מותאם",
        ingredients=[Ingredient(name="חזה עוף", amount="500 גרם"), Ingredient(name="ביצה")],
        instructions=["לשטוף את החזה", "לטגן עד להזהבה"],
        cooking_tips=["לחמם את השמן היטב לפני הטיגון"],
    )


async def _seed_awaiting_delivery_mode(session_factory, chat_id: int) -> None:
    async with session_factory() as db_session:
        await SessionRepository(db_session).upsert(
            SessionData(
                chat_id=chat_id,
                state=SessionState.AWAITING_DELIVERY_MODE,
                final_recipe=_final_recipe(),
            )
        )


async def test_full_mode_renders_recipe_and_completes_session(context_with_db, session_factory):
    update = make_callback_update("mode:full", chat_id=1)
    await _seed_awaiting_delivery_mode(session_factory, 1)

    await handle_mode_choice(update, context_with_db)

    call = update.callback_query.edit_message_text.call_args
    message = call.args[0]
    assert "שניצל עוף מותאם" in message
    assert "חזה עוף" in message
    assert "לטגן עד להזהבה" in message
    assert "לחמם את השמן היטב לפני הטיגון" in message
    assert call.kwargs["reply_markup"] is not None

    async with session_factory() as db_session:
        session = await SessionRepository(db_session).get_by_chat_id(1)
        history = await RecipeHistoryRepository(db_session).list_for_user(456)

    assert session.state == SessionState.COMPLETED
    assert session.delivery_mode == "full"
    assert session.history_logged is True
    assert len(history) == 1


async def test_interactive_mode_renders_first_step(context_with_db, session_factory):
    update = make_callback_update("mode:interactive", chat_id=2)
    await _seed_awaiting_delivery_mode(session_factory, 2)

    await handle_mode_choice(update, context_with_db)

    message = update.callback_query.edit_message_text.call_args.args[0]
    assert "שלב 1 מתוך 2" in message
    assert "לשטוף את החזה" in message

    async with session_factory() as db_session:
        session = await SessionRepository(db_session).get_by_chat_id(2)

    assert session.state == SessionState.DELIVERING_INTERACTIVE
    assert session.delivery_mode == "interactive"
    assert session.current_step_index == 0


async def test_switch_from_full_to_interactive_resumes_current_step(
    context_with_db, session_factory
):
    async with session_factory() as db_session:
        await SessionRepository(db_session).upsert(
            SessionData(
                chat_id=5,
                state=SessionState.COMPLETED,
                final_recipe=_final_recipe(),
                delivery_mode="full",
                current_step_index=1,
                history_logged=True,
            )
        )
    update = make_callback_update("mode:interactive", chat_id=5)

    await handle_mode_choice(update, context_with_db)

    message = update.callback_query.edit_message_text.call_args.args[0]
    assert "שלב 2 מתוך 2" in message

    async with session_factory() as db_session:
        session = await SessionRepository(db_session).get_by_chat_id(5)

    assert session.state == SessionState.DELIVERING_INTERACTIVE
    assert session.current_step_index == 1


async def test_switch_from_interactive_to_full_shows_toggle_button(
    context_with_db, session_factory
):
    async with session_factory() as db_session:
        await SessionRepository(db_session).upsert(
            SessionData(
                chat_id=6,
                state=SessionState.DELIVERING_INTERACTIVE,
                final_recipe=_final_recipe(),
                delivery_mode="interactive",
                current_step_index=1,
            )
        )
    update = make_callback_update("mode:full", chat_id=6)

    await handle_mode_choice(update, context_with_db)

    call = update.callback_query.edit_message_text.call_args
    assert "שניצל עוף מותאם" in call.args[0]
    keyboard = call.kwargs["reply_markup"]
    callback_data = [button.callback_data for row in keyboard.inline_keyboard for button in row]
    assert callback_data == ["mode:interactive"]

    async with session_factory() as db_session:
        session = await SessionRepository(db_session).get_by_chat_id(6)

    assert session.state == SessionState.COMPLETED
    assert session.delivery_mode == "full"
    # Switching back to full doesn't lose interactive progress.
    assert session.current_step_index == 1


async def test_toggling_modes_only_logs_history_once(context_with_db, session_factory):
    async with session_factory() as db_session:
        await SessionRepository(db_session).upsert(
            SessionData(
                chat_id=7,
                state=SessionState.AWAITING_DELIVERY_MODE,
                final_recipe=_final_recipe(),
            )
        )

    await handle_mode_choice(make_callback_update("mode:full", chat_id=7), context_with_db)
    await handle_mode_choice(make_callback_update("mode:interactive", chat_id=7), context_with_db)
    await handle_mode_choice(make_callback_update("mode:full", chat_id=7), context_with_db)

    async with session_factory() as db_session:
        history = await RecipeHistoryRepository(db_session).list_for_user(456)

    assert len(history) == 1


async def test_rejects_when_not_awaiting_delivery_mode(context_with_db, session_factory):
    update = make_callback_update("mode:full", chat_id=3)
    # No session seeded -> defaults to IDLE.

    await handle_mode_choice(update, context_with_db)

    update.callback_query.edit_message_text.assert_awaited_once_with(
        labels.STALE_SELECTION_MESSAGE
    )


async def test_rejects_when_final_recipe_missing(context_with_db, session_factory):
    update = make_callback_update("mode:full", chat_id=4)
    async with session_factory() as db_session:
        await SessionRepository(db_session).upsert(
            SessionData(chat_id=4, state=SessionState.AWAITING_DELIVERY_MODE, final_recipe=None)
        )

    await handle_mode_choice(update, context_with_db)

    update.callback_query.edit_message_text.assert_awaited_once_with(
        labels.STALE_SELECTION_MESSAGE
    )


def test_build_full_recipe_message_includes_all_sections():
    message = build_full_recipe_message(_final_recipe())

    assert labels.FULL_RECIPE_INGREDIENTS_HEADER in message
    assert labels.FULL_RECIPE_INSTRUCTIONS_HEADER in message
    assert labels.FULL_RECIPE_TIPS_HEADER in message
    assert "1. לשטוף את החזה" in message
    assert "2. לטגן עד להזהבה" in message


def test_build_full_recipe_message_omits_tips_section_when_no_tips():
    recipe = FinalRecipe(
        recipe_name="מתכון", ingredients=[Ingredient(name="מלח")], instructions=["לבשל"]
    )
    message = build_full_recipe_message(recipe)

    assert labels.FULL_RECIPE_TIPS_HEADER not in message


def test_build_delivery_mode_keyboard_has_both_modes():
    keyboard = build_delivery_mode_keyboard()
    callback_data = [button.callback_data for row in keyboard.inline_keyboard for button in row]

    assert callback_data == ["mode:interactive", "mode:full"]


def test_build_full_recipe_keyboard_offers_switch_to_interactive():
    keyboard = build_full_recipe_keyboard()
    callback_data = [button.callback_data for row in keyboard.inline_keyboard for button in row]

    assert callback_data == ["mode:interactive"]
