from app.database.session_repository import SessionRepository
from app.handlers.checklist_handler import handle_finished, handle_toggle
from app.models.recipe import Ingredient, StructuredRecipe
from app.models.session import ChecklistItem, SessionData, SessionState
from app.static import labels
from tests.conftest import make_callback_update


def _structured() -> StructuredRecipe:
    return StructuredRecipe(
        recipe_name="שניצל עוף",
        ingredients=[Ingredient(name="חזה עוף", amount="500 גרם"), Ingredient(name="ביצה")],
        instructions=["לשטוף", "לטגן"],
    )


async def _seed_awaiting_checklist(session_factory, chat_id: int) -> None:
    async with session_factory() as db_session:
        await SessionRepository(db_session).upsert(
            SessionData(
                chat_id=chat_id,
                state=SessionState.AWAITING_CHECKLIST,
                structured_recipe=_structured(),
                checklist=[
                    ChecklistItem(name="חזה עוף", amount="500 גרם", checked=True),
                    ChecklistItem(name="ביצה", checked=True),
                ],
            )
        )


async def test_toggle_flips_checked_state_and_persists(context_with_db, session_factory):
    update = make_callback_update("toggle:1", chat_id=1)
    await _seed_awaiting_checklist(session_factory, 1)

    await handle_toggle(update, context_with_db)

    async with session_factory() as db_session:
        session = await SessionRepository(db_session).get_by_chat_id(1)

    assert session.checklist[1].checked is False
    assert session.checklist[0].checked is True


async def test_toggle_re_renders_keyboard_in_place(context_with_db, session_factory):
    update = make_callback_update("toggle:1", chat_id=2)
    await _seed_awaiting_checklist(session_factory, 2)

    await handle_toggle(update, context_with_db)

    update.callback_query.edit_message_text.assert_awaited_once()
    _, kwargs = update.callback_query.edit_message_text.call_args
    keyboard = kwargs["reply_markup"]
    button_labels = [button.text for row in keyboard.inline_keyboard for button in row]
    assert any("⬜" in label and "ביצה" in label for label in button_labels)


async def test_toggle_rejects_stale_index(context_with_db, session_factory):
    update = make_callback_update("toggle:9", chat_id=3)
    await _seed_awaiting_checklist(session_factory, 3)

    await handle_toggle(update, context_with_db)

    update.callback_query.edit_message_text.assert_awaited_once_with(
        labels.STALE_SELECTION_MESSAGE
    )


async def test_toggle_rejects_when_not_awaiting_checklist(context_with_db, session_factory):
    update = make_callback_update("toggle:0", chat_id=4)
    # No session seeded -> defaults to IDLE.

    await handle_toggle(update, context_with_db)

    update.callback_query.edit_message_text.assert_awaited_once_with(
        labels.STALE_SELECTION_MESSAGE
    )


async def test_finished_transitions_to_deciding_substitutions(context_with_db, session_factory):
    update = make_callback_update("finished", chat_id=5)
    await _seed_awaiting_checklist(session_factory, 5)

    await handle_finished(update, context_with_db)

    update.callback_query.edit_message_text.assert_awaited_once_with(
        labels.PROCESSING_CHECKLIST_MESSAGE
    )

    async with session_factory() as db_session:
        session = await SessionRepository(db_session).get_by_chat_id(5)

    assert session.state == SessionState.DECIDING_SUBSTITUTIONS


async def test_finished_rejects_when_not_awaiting_checklist(context_with_db, session_factory):
    update = make_callback_update("finished", chat_id=6)

    await handle_finished(update, context_with_db)

    update.callback_query.edit_message_text.assert_awaited_once_with(
        labels.STALE_SELECTION_MESSAGE
    )
