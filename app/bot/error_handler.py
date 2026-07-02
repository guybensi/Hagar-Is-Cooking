from telegram import Update
from telegram.ext import ContextTypes

from app.utils.logging import get_logger

logger = get_logger(__name__)

GENERIC_ERROR_MESSAGE = "אופס, קרתה תקלה 😅 אפשר לנסות שוב?"


async def handle_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Global error boundary: log the failure and, if possible, reply to the user in Hebrew.

    Registered via Application.add_error_handler so no exception raised inside a handler
    can crash the polling loop.
    """
    logger.error("unhandled_exception", error=str(context.error), exc_info=context.error)

    if isinstance(update, Update) and update.effective_chat is not None:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id, text=GENERIC_ERROR_MESSAGE
            )
        except Exception:
            logger.error("failed_to_send_error_message", exc_info=True)
