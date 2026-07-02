from unittest.mock import AsyncMock

from app.database.session_repository import SessionRepository
from app.handlers.substitution_handler import (
    build_substitution_keyboard,
    build_substitution_question_message,
    handle_answer,
    substitute_decisions,
)
from app.models.recipe import FinalRecipe, Ingredient
from app.models.session import SessionData, SessionState
from app.models.substitution import SubstitutionAction, SubstitutionAnswer, SubstitutionDecision
from app.services.final_recipe_service import FinalRecipeGenerationError
from app.static import labels
from tests.conftest import make_callback_update


def _decisions() -> list[SubstitutionDecision]:
    return [
        SubstitutionDecision(
            ingredient_name="ביצה", action=SubstitutionAction.BUY, reason="חשוב"
        ),
        SubstitutionDecision(
            ingredient_name="שורש סלרי",
            action=SubstitutionAction.SUBSTITUTE,
            reason="דומה",
            replacement="שורש פטרוזיליה",
        ),
        SubstitutionDecision(
            ingredient_name="בזיליקום",
            action=SubstitutionAction.SUBSTITUTE,
            reason="דומה",
            replacement="אורגנו",
        ),
    ]


async def _seed_awaiting_answers(session_factory, chat_id: int, *, pending_index: int) -> None:
    async with session_factory() as db_session:
        await SessionRepository(db_session).upsert(
            SessionData(
                chat_id=chat_id,
                state=SessionState.AWAITING_SUBSTITUTION_ANSWERS,
                substitution_decisions=_decisions(),
                substitution_answers=[
                    SubstitutionAnswer(ingredient_name="שורש סלרי"),
                    SubstitutionAnswer(ingredient_name="בזיליקום"),
                ],
                pending_substitution_index=pending_index,
            )
        )


async def test_answering_first_of_two_shows_next_question(context_with_db, session_factory):
    update = make_callback_update("sub:0:yes", chat_id=1)
    await _seed_awaiting_answers(session_factory, 1, pending_index=0)

    await handle_answer(update, context_with_db)

    final_call = update.callback_query.edit_message_text.call_args_list[-1]
    assert "בזיליקום" in final_call.args[0]
    assert final_call.kwargs["reply_markup"] is not None

    async with session_factory() as db_session:
        session = await SessionRepository(db_session).get_by_chat_id(1)

    assert session.state == SessionState.AWAITING_SUBSTITUTION_ANSWERS
    assert session.pending_substitution_index == 1
    assert session.substitution_answers[0].accepted is True
    assert session.substitution_answers[1].accepted is None


async def test_answering_last_pending_generates_final_recipe(context_with_db, session_factory):
    update = make_callback_update("sub:1:no", chat_id=2)
    await _seed_awaiting_answers(session_factory, 2, pending_index=1)

    final_recipe_service = AsyncMock()
    final_recipe_service.generate.return_value = FinalRecipe(
        recipe_name="שניצל מותאם",
        ingredients=[Ingredient(name="חזה עוף")],
        instructions=["לטגן"],
    )
    context_with_db.bot_data["final_recipe_service"] = final_recipe_service

    await handle_answer(update, context_with_db)

    calls = update.callback_query.edit_message_text.call_args_list
    assert calls[0].args[0] == labels.GENERATING_FINAL_MESSAGE
    assert "שניצל מותאם" in calls[1].args[0]
    assert labels.DELIVERY_MODE_PROMPT in calls[1].args[0]
    assert calls[1].kwargs["reply_markup"] is not None

    async with session_factory() as db_session:
        session = await SessionRepository(db_session).get_by_chat_id(2)

    assert session.state == SessionState.AWAITING_DELIVERY_MODE
    assert session.substitution_answers[1].accepted is False
    assert session.final_recipe.recipe_name == "שניצל מותאם"


async def test_answering_last_pending_reverts_on_final_recipe_generation_failure(
    context_with_db, session_factory
):
    update = make_callback_update("sub:1:yes", chat_id=5)
    await _seed_awaiting_answers(session_factory, 5, pending_index=1)

    final_recipe_service = AsyncMock()
    final_recipe_service.generate.side_effect = FinalRecipeGenerationError("boom")
    context_with_db.bot_data["final_recipe_service"] = final_recipe_service

    await handle_answer(update, context_with_db)

    final_call = update.callback_query.edit_message_text.call_args_list[-1]
    assert final_call.args[0] == labels.FINAL_RECIPE_FAILED_MESSAGE

    async with session_factory() as db_session:
        session = await SessionRepository(db_session).get_by_chat_id(5)

    assert session.state == SessionState.AWAITING_CHECKLIST


async def test_answer_rejects_out_of_order_index(context_with_db, session_factory):
    update = make_callback_update("sub:1:yes", chat_id=3)
    await _seed_awaiting_answers(session_factory, 3, pending_index=0)

    await handle_answer(update, context_with_db)

    update.callback_query.edit_message_text.assert_awaited_once_with(
        labels.STALE_SELECTION_MESSAGE
    )


async def test_answer_rejects_when_not_awaiting_substitution_answers(
    context_with_db, session_factory
):
    update = make_callback_update("sub:0:yes", chat_id=4)
    # No session seeded -> defaults to IDLE.

    await handle_answer(update, context_with_db)

    update.callback_query.edit_message_text.assert_awaited_once_with(
        labels.STALE_SELECTION_MESSAGE
    )


def test_substitute_decisions_filters_to_only_substitute_action():
    filtered = substitute_decisions(_decisions())

    assert [d.ingredient_name for d in filtered] == ["שורש סלרי", "בזיליקום"]


def test_build_substitution_question_message_includes_ingredient_and_replacement():
    decision = _decisions()[1]
    message = build_substitution_question_message(decision)

    assert "שורש סלרי" in message
    assert "שורש פטרוזיליה" in message


def test_build_substitution_keyboard_has_yes_no_buttons_with_index():
    keyboard = build_substitution_keyboard(2)
    callback_data = [button.callback_data for row in keyboard.inline_keyboard for button in row]

    assert callback_data == ["sub:2:yes", "sub:2:no", "cancel"]
