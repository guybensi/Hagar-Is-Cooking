from app.handlers.start_handler import (
    CANCEL_MESSAGE,
    HELP_MESSAGE,
    WELCOME_MESSAGE,
    cancel,
    help_command,
    start,
)
from tests.conftest import make_context, make_update


async def test_start_replies_with_welcome_message():
    update = make_update(text="/start")
    context = make_context()

    await start(update, context)

    update.message.reply_text.assert_awaited_once_with(WELCOME_MESSAGE)


async def test_help_replies_with_help_message():
    update = make_update(text="/help")
    context = make_context()

    await help_command(update, context)

    update.message.reply_text.assert_awaited_once_with(HELP_MESSAGE)


async def test_cancel_replies_with_cancel_message():
    update = make_update(text="/cancel")
    context = make_context()

    await cancel(update, context)

    update.message.reply_text.assert_awaited_once_with(CANCEL_MESSAGE)
