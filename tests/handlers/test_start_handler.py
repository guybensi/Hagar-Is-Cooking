from app.database.engine import session_scope
from app.database.session_repository import SessionRepository
from app.database.user_repository import UserRepository
from app.handlers.start_handler import cancel, handle_cancel_callback, help_command, start
from app.models.recipe import FinalRecipe, Ingredient, StructuredRecipe
from app.models.search import SearchResult
from app.models.session import ChecklistItem, SessionData, SessionState
from app.models.substitution import SubstitutionAction, SubstitutionAnswer, SubstitutionDecision
from app.static import labels
from tests.conftest import make_callback_update, make_context, make_update


async def test_start_replies_with_welcome_message(context_with_db, session_factory):
    update = make_update(text="/start")

    await start(update, context_with_db)

    update.message.reply_text.assert_awaited_once_with(labels.WELCOME_MESSAGE)


async def test_start_registers_the_user(context_with_db, session_factory):
    update = make_update(text="/start", user_id=789)

    await start(update, context_with_db)

    async with session_scope(session_factory) as db_session:
        record = await UserRepository(db_session).get_or_create(789, "test_user")

    assert record.telegram_user_id == 789


async def test_help_replies_with_help_message():
    update = make_update(text="/help")
    context = make_context()

    await help_command(update, context)

    update.message.reply_text.assert_awaited_once_with(labels.HELP_MESSAGE)


async def test_cancel_replies_with_cancel_message(context_with_db):
    update = make_update(text="/cancel")

    await cancel(update, context_with_db)

    update.message.reply_text.assert_awaited_once_with(labels.CANCEL_MESSAGE)


async def test_cancel_resets_session_to_idle(context_with_db, session_factory):
    update = make_update(text="/cancel", chat_id=555)

    async with session_scope(session_factory) as db_session:
        repo = SessionRepository(db_session)
        await repo.upsert(SessionData(chat_id=555, state=SessionState.AWAITING_CHECKLIST))

    await cancel(update, context_with_db)

    async with session_scope(session_factory) as db_session:
        session = await SessionRepository(db_session).get_by_chat_id(555)

    assert session.state == SessionState.IDLE


async def test_cancel_button_resets_session_and_edits_message(context_with_db, session_factory):
    update = make_callback_update("cancel", chat_id=556)

    async with session_scope(session_factory) as db_session:
        repo = SessionRepository(db_session)
        await repo.upsert(SessionData(chat_id=556, state=SessionState.AWAITING_CHECKLIST))

    await handle_cancel_callback(update, context_with_db)

    update.callback_query.answer.assert_awaited_once()
    update.callback_query.edit_message_text.assert_awaited_once_with(labels.CANCEL_MESSAGE)

    async with session_scope(session_factory) as db_session:
        session = await SessionRepository(db_session).get_by_chat_id(556)

    assert session.state == SessionState.IDLE


async def test_start_resumes_recipe_selection_mid_flow(context_with_db, session_factory):
    update = make_update(text="/start", chat_id=601)

    async with session_scope(session_factory) as db_session:
        await SessionRepository(db_session).upsert(
            SessionData(
                chat_id=601,
                state=SessionState.AWAITING_RECIPE_SELECTION,
                search_results=[
                    SearchResult(title="שניצל א", url="https://www.mako.co.il/food/a")
                ],
            )
        )

    await start(update, context_with_db)

    calls = update.message.reply_text.call_args_list
    assert calls[0].args[0] == labels.RESUME_PROMPT
    assert "שניצל א" in calls[1].args[0]
    assert calls[1].kwargs["reply_markup"] is not None


async def test_start_resumes_checklist_mid_flow(context_with_db, session_factory):
    update = make_update(text="/start", chat_id=602)

    async with session_scope(session_factory) as db_session:
        await SessionRepository(db_session).upsert(
            SessionData(
                chat_id=602,
                state=SessionState.AWAITING_CHECKLIST,
                structured_recipe=StructuredRecipe(
                    recipe_name="שניצל עוף",
                    ingredients=[Ingredient(name="חזה עוף")],
                    instructions=["לטגן"],
                ),
                checklist=[ChecklistItem(name="חזה עוף", checked=True)],
            )
        )

    await start(update, context_with_db)

    calls = update.message.reply_text.call_args_list
    assert calls[0].args[0] == labels.RESUME_PROMPT
    assert "שניצל עוף" in calls[1].args[0]
    assert calls[1].kwargs["reply_markup"] is not None


async def test_start_resumes_substitution_question_mid_flow(context_with_db, session_factory):
    update = make_update(text="/start", chat_id=603)

    async with session_scope(session_factory) as db_session:
        await SessionRepository(db_session).upsert(
            SessionData(
                chat_id=603,
                state=SessionState.AWAITING_SUBSTITUTION_ANSWERS,
                substitution_decisions=[
                    SubstitutionDecision(
                        ingredient_name="שורש סלרי",
                        action=SubstitutionAction.SUBSTITUTE,
                        reason="דומה",
                        replacement="שורש פטרוזיליה",
                    )
                ],
                substitution_answers=[SubstitutionAnswer(ingredient_name="שורש סלרי")],
                pending_substitution_index=0,
            )
        )

    await start(update, context_with_db)

    calls = update.message.reply_text.call_args_list
    assert calls[0].args[0] == labels.RESUME_PROMPT
    assert "שורש סלרי" in calls[1].args[0]


async def test_start_resumes_delivery_mode_mid_flow(context_with_db, session_factory):
    update = make_update(text="/start", chat_id=604)

    async with session_scope(session_factory) as db_session:
        await SessionRepository(db_session).upsert(
            SessionData(
                chat_id=604,
                state=SessionState.AWAITING_DELIVERY_MODE,
                final_recipe=FinalRecipe(
                    recipe_name="שניצל עוף",
                    ingredients=[Ingredient(name="חזה עוף")],
                    instructions=["לטגן"],
                ),
            )
        )

    await start(update, context_with_db)

    calls = update.message.reply_text.call_args_list
    assert calls[0].args[0] == labels.RESUME_PROMPT
    assert "שניצל עוף" in calls[1].args[0]
    assert calls[1].kwargs["reply_markup"] is not None


async def test_start_resumes_interactive_step_mid_flow(context_with_db, session_factory):
    update = make_update(text="/start", chat_id=605)

    async with session_scope(session_factory) as db_session:
        await SessionRepository(db_session).upsert(
            SessionData(
                chat_id=605,
                state=SessionState.DELIVERING_INTERACTIVE,
                final_recipe=FinalRecipe(
                    recipe_name="שניצל עוף",
                    ingredients=[Ingredient(name="חזה עוף")],
                    instructions=["לשטוף", "לטגן"],
                ),
                current_step_index=1,
            )
        )

    await start(update, context_with_db)

    calls = update.message.reply_text.call_args_list
    assert calls[0].args[0] == labels.RESUME_PROMPT
    assert "שלב 2 מתוך 2" in calls[1].args[0]


async def test_start_resets_transient_state_and_shows_welcome(context_with_db, session_factory):
    update = make_update(text="/start", chat_id=606)

    async with session_scope(session_factory) as db_session:
        await SessionRepository(db_session).upsert(
            SessionData(chat_id=606, state=SessionState.STRUCTURING)
        )

    await start(update, context_with_db)

    update.message.reply_text.assert_awaited_once_with(labels.WELCOME_MESSAGE)

    async with session_scope(session_factory) as db_session:
        session = await SessionRepository(db_session).get_by_chat_id(606)

    assert session.state == SessionState.IDLE
