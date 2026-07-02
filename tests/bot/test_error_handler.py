from app.bot.error_handler import GENERIC_ERROR_MESSAGE, handle_error
from tests.conftest import make_context, make_update


async def test_handle_error_sends_hebrew_message_to_effective_chat():
    update = make_update(chat_id=999)
    context = make_context()
    context.error = RuntimeError("boom")

    await handle_error(update, context)

    context.bot.send_message.assert_awaited_once_with(chat_id=999, text=GENERIC_ERROR_MESSAGE)


async def test_handle_error_swallows_failure_to_notify_user():
    update = make_update(chat_id=999)
    context = make_context()
    context.error = RuntimeError("boom")
    context.bot.send_message.side_effect = RuntimeError("telegram is down too")

    # Must not raise -- the error boundary can never crash the bot.
    await handle_error(update, context)


async def test_handle_error_handles_update_without_effective_chat():
    context = make_context()
    context.error = RuntimeError("boom")

    # `update` isn't a telegram.Update instance at all (e.g. a raw exception context) --
    # handler must not crash.
    await handle_error(object(), context)

    context.bot.send_message.assert_not_awaited()
