from app.database.session_repository import SessionRepository
from app.handlers.delivery_handler import (
    build_delivery_mode_keyboard,
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

    message = update.callback_query.edit_message_text.call_args.args[0]
    assert "שניצל עוף מותאם" in message
    assert "חזה עוף" in message
    assert "לטגן עד להזהבה" in message
    assert "לחמם את השמן היטב לפני הטיגון" in message

    async with session_factory() as db_session:
        session = await SessionRepository(db_session).get_by_chat_id(1)

    assert session.state == SessionState.COMPLETED
    assert session.delivery_mode == "full"


async def test_interactive_mode_transitions_to_delivering_interactive(
    context_with_db, session_factory
):
    update = make_callback_update("mode:interactive", chat_id=2)
    await _seed_awaiting_delivery_mode(session_factory, 2)

    await handle_mode_choice(update, context_with_db)

    update.callback_query.edit_message_text.assert_awaited_once_with(
        labels.INTERACTIVE_MODE_COMING_SOON_MESSAGE
    )

    async with session_factory() as db_session:
        session = await SessionRepository(db_session).get_by_chat_id(2)

    assert session.state == SessionState.DELIVERING_INTERACTIVE
    assert session.delivery_mode == "interactive"


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
