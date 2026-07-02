from unittest.mock import AsyncMock

from app.database.session_repository import SessionRepository
from app.handlers.checklist_handler import handle_finished, handle_toggle
from app.models.recipe import FinalRecipe, Ingredient, StructuredRecipe
from app.models.session import ChecklistItem, SessionData, SessionState
from app.models.substitution import SubstitutionAction, SubstitutionDecision
from app.services.substitution_service import SubstitutionDecisionError
from app.static import labels
from tests.conftest import make_callback_update


def _fake_final_recipe_service() -> AsyncMock:
    service = AsyncMock()
    service.generate.return_value = FinalRecipe(
        recipe_name="שניצל מותאם", ingredients=[Ingredient(name="חזה עוף")], instructions=["לטגן"]
    )
    return service


def _structured() -> StructuredRecipe:
    return StructuredRecipe(
        recipe_name="שניצל עוף",
        ingredients=[Ingredient(name="חזה עוף", amount="500 גרם"), Ingredient(name="ביצה")],
        instructions=["לשטוף", "לטגן"],
    )


async def _seed_awaiting_checklist(session_factory, chat_id: int, *, all_checked: bool) -> None:
    async with session_factory() as db_session:
        await SessionRepository(db_session).upsert(
            SessionData(
                chat_id=chat_id,
                state=SessionState.AWAITING_CHECKLIST,
                structured_recipe=_structured(),
                checklist=[
                    ChecklistItem(name="חזה עוף", amount="500 גרם", checked=True),
                    ChecklistItem(name="ביצה", checked=all_checked),
                ],
            )
        )


async def test_toggle_flips_checked_state_and_persists(context_with_db, session_factory):
    update = make_callback_update("toggle:1", chat_id=1)
    await _seed_awaiting_checklist(session_factory, 1, all_checked=True)

    await handle_toggle(update, context_with_db)

    async with session_factory() as db_session:
        session = await SessionRepository(db_session).get_by_chat_id(1)

    assert session.checklist[1].checked is False
    assert session.checklist[0].checked is True


async def test_toggle_re_renders_keyboard_in_place(context_with_db, session_factory):
    update = make_callback_update("toggle:1", chat_id=2)
    await _seed_awaiting_checklist(session_factory, 2, all_checked=True)

    await handle_toggle(update, context_with_db)

    update.callback_query.edit_message_text.assert_awaited_once()
    _, kwargs = update.callback_query.edit_message_text.call_args
    keyboard = kwargs["reply_markup"]
    button_labels = [button.text for row in keyboard.inline_keyboard for button in row]
    assert any("⬜" in label and "ביצה" in label for label in button_labels)


async def test_toggle_rejects_stale_index(context_with_db, session_factory):
    update = make_callback_update("toggle:9", chat_id=3)
    await _seed_awaiting_checklist(session_factory, 3, all_checked=True)

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


async def test_finished_with_no_missing_ingredients_skips_straight_to_final_recipe(
    context_with_db, session_factory
):
    update = make_callback_update("finished", chat_id=5)
    await _seed_awaiting_checklist(session_factory, 5, all_checked=True)
    context_with_db.bot_data["final_recipe_service"] = _fake_final_recipe_service()

    await handle_finished(update, context_with_db)

    calls = update.callback_query.edit_message_text.call_args_list
    assert calls[0].args[0] == labels.GENERATING_FINAL_MESSAGE
    assert "שניצל מותאם" in calls[1].args[0]
    assert calls[1].kwargs["reply_markup"] is not None

    async with session_factory() as db_session:
        session = await SessionRepository(db_session).get_by_chat_id(5)

    assert session.state == SessionState.AWAITING_DELIVERY_MODE
    assert session.final_recipe.recipe_name == "שניצל מותאם"


async def test_finished_with_no_substitute_decisions_skips_to_final_recipe(
    context_with_db, session_factory
):
    update = make_callback_update("finished", chat_id=6)
    await _seed_awaiting_checklist(session_factory, 6, all_checked=False)

    substitution_service = AsyncMock()
    substitution_service.decide.return_value = [
        SubstitutionDecision(
            ingredient_name="ביצה", action=SubstitutionAction.SKIP, reason="לא חובה"
        )
    ]
    context_with_db.bot_data["substitution_service"] = substitution_service
    context_with_db.bot_data["final_recipe_service"] = _fake_final_recipe_service()

    await handle_finished(update, context_with_db)

    calls = update.callback_query.edit_message_text.call_args_list
    assert calls[0].args[0] == labels.PROCESSING_CHECKLIST_MESSAGE
    assert calls[1].args[0] == labels.GENERATING_FINAL_MESSAGE
    assert "שניצל מותאם" in calls[2].args[0]
    assert calls[2].kwargs["reply_markup"] is not None

    async with session_factory() as db_session:
        session = await SessionRepository(db_session).get_by_chat_id(6)

    assert session.state == SessionState.AWAITING_DELIVERY_MODE
    assert len(session.substitution_decisions) == 1


async def test_finished_with_substitute_decision_asks_the_first_question(
    context_with_db, session_factory
):
    update = make_callback_update("finished", chat_id=7)
    await _seed_awaiting_checklist(session_factory, 7, all_checked=False)

    substitution_service = AsyncMock()
    substitution_service.decide.return_value = [
        SubstitutionDecision(
            ingredient_name="ביצה",
            action=SubstitutionAction.SUBSTITUTE,
            reason="דומה",
            replacement="תחליף ביצים",
        )
    ]
    context_with_db.bot_data["substitution_service"] = substitution_service

    await handle_finished(update, context_with_db)

    final_call = update.callback_query.edit_message_text.call_args_list[-1]
    assert "ביצה" in final_call.args[0]
    assert "תחליף ביצים" in final_call.args[0]
    assert final_call.kwargs["reply_markup"] is not None

    async with session_factory() as db_session:
        session = await SessionRepository(db_session).get_by_chat_id(7)

    assert session.state == SessionState.AWAITING_SUBSTITUTION_ANSWERS
    assert session.pending_substitution_index == 0
    assert len(session.substitution_answers) == 1
    assert session.substitution_answers[0].accepted is None


async def test_finished_reverts_to_checklist_on_substitution_failure(
    context_with_db, session_factory
):
    update = make_callback_update("finished", chat_id=8)
    await _seed_awaiting_checklist(session_factory, 8, all_checked=False)

    substitution_service = AsyncMock()
    substitution_service.decide.side_effect = SubstitutionDecisionError("boom")
    context_with_db.bot_data["substitution_service"] = substitution_service

    await handle_finished(update, context_with_db)

    final_call = update.callback_query.edit_message_text.call_args_list[-1]
    assert final_call.args[0] == labels.SUBSTITUTION_FAILED_MESSAGE

    async with session_factory() as db_session:
        session = await SessionRepository(db_session).get_by_chat_id(8)

    assert session.state == SessionState.AWAITING_CHECKLIST


async def test_finished_rejects_when_not_awaiting_checklist(context_with_db, session_factory):
    update = make_callback_update("finished", chat_id=9)

    await handle_finished(update, context_with_db)

    update.callback_query.edit_message_text.assert_awaited_once_with(
        labels.STALE_SELECTION_MESSAGE
    )
