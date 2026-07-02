from telegram.constants import ChatAction

from app.utils.telegram_helpers import edit_or_send, typing_action
from tests.conftest import make_context


async def test_edit_or_send_edits_when_message_id_given():
    context = make_context()

    await edit_or_send(context, chat_id=1, text="hello", message_id=42)

    context.bot.edit_message_text.assert_awaited_once_with(
        chat_id=1, message_id=42, text="hello", reply_markup=None
    )
    context.bot.send_message.assert_not_awaited()


async def test_edit_or_send_falls_back_to_send_when_edit_fails():
    context = make_context()
    context.bot.edit_message_text.side_effect = RuntimeError("message too old")

    await edit_or_send(context, chat_id=1, text="hello", message_id=42)

    context.bot.send_message.assert_awaited_once_with(chat_id=1, text="hello", reply_markup=None)


async def test_edit_or_send_sends_when_no_message_id():
    context = make_context()

    await edit_or_send(context, chat_id=1, text="hello")

    context.bot.send_message.assert_awaited_once_with(chat_id=1, text="hello", reply_markup=None)
    context.bot.edit_message_text.assert_not_awaited()


async def test_typing_action_sends_typing_chat_action():
    context = make_context()

    async with typing_action(context, chat_id=1):
        pass

    context.bot.send_chat_action.assert_awaited_once_with(chat_id=1, action=ChatAction.TYPING)
