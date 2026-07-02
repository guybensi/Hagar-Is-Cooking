from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from app.static import labels
from app.utils.logging import get_logger

logger = get_logger(__name__)


def cancel_row() -> list[InlineKeyboardButton]:
    """A keyboard row offering to cancel whatever's in progress and start a new recipe.

    Appended to every in-flow keyboard (search results, checklist, substitution questions,
    delivery mode, full recipe, interactive steps) so the user can always bail out, regardless
    of which step they're on.
    """
    return [InlineKeyboardButton(labels.CANCEL_BUTTON, callback_data="cancel")]


async def edit_or_send(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    text: str,
    *,
    message_id: int | None = None,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> Message:
    """Edit an existing bot message in place when possible, otherwise send a new one.

    Falls back to sending a fresh message if the edit fails (message too old, deleted, or
    content unchanged) so the user always sees a response rather than a silent failure.
    """
    if message_id is not None:
        try:
            return await context.bot.edit_message_text(
                chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup
            )
        except Exception:
            logger.debug("edit_message_failed_falling_back_to_send", chat_id=chat_id)

    return await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)


@asynccontextmanager
async def typing_action(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> AsyncIterator[None]:
    """Show the Telegram 'typing...' indicator while a slow operation runs."""
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    yield
