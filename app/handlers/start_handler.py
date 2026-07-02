from telegram import Update
from telegram.ext import ContextTypes

from app.database.engine import session_scope
from app.database.session_repository import SessionRepository
from app.database.user_repository import UserRepository
from app.services.session_service import SessionService
from app.static import labels
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user = update.effective_user
    logger.info("start_command", chat_id=chat_id)

    session_factory = context.bot_data["session_factory"]
    async with session_scope(session_factory) as db_session:
        await UserRepository(db_session).get_or_create(user.id, user.username)

    await update.message.reply_text(labels.WELCOME_MESSAGE)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(labels.HELP_MESSAGE)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    logger.info("cancel_command", chat_id=chat_id)

    session_factory = context.bot_data["session_factory"]
    async with session_scope(session_factory) as db_session:
        await SessionService(SessionRepository(db_session)).reset(chat_id)

    await update.message.reply_text(labels.CANCEL_MESSAGE)
