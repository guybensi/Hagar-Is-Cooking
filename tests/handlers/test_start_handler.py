from app.database.engine import session_scope
from app.database.session_repository import SessionRepository
from app.database.user_repository import UserRepository
from app.handlers.start_handler import cancel, help_command, start
from app.models.session import SessionData, SessionState
from app.static import labels
from tests.conftest import make_context, make_update


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
