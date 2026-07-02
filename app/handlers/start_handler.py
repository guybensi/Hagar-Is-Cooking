from telegram import InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.database.engine import session_scope
from app.database.session_repository import SessionRepository
from app.database.user_repository import UserRepository
from app.handlers import checklist_handler, delivery_handler, interactive_handler, search_handler
from app.handlers.substitution_handler import (
    build_substitution_keyboard,
    build_substitution_question_message,
    substitute_decisions,
)
from app.models.session import QUERY_ACCEPTING_STATES, TRANSIENT_STATES, SessionData, SessionState
from app.services.session_service import SessionService
from app.static import labels
from app.utils.logging import bind_chat_context, get_logger

logger = get_logger(__name__)


def _build_resume_content(session: SessionData) -> tuple[str, InlineKeyboardMarkup] | None:
    """Re-render whatever the user was looking at before a restart, if it's recoverable."""
    if session.state == SessionState.AWAITING_RECIPE_SELECTION:
        return (
            search_handler.build_results_message(session.search_results),
            search_handler.build_results_keyboard(session.search_results),
        )

    if session.state == SessionState.AWAITING_CHECKLIST:
        return (
            checklist_handler.build_checklist_message(session.structured_recipe.recipe_name),
            checklist_handler.build_checklist_keyboard(session.checklist),
        )

    if session.state == SessionState.AWAITING_SUBSTITUTION_ANSWERS:
        pending = substitute_decisions(session.substitution_decisions)
        decision = pending[session.pending_substitution_index]
        return (
            build_substitution_question_message(decision),
            build_substitution_keyboard(session.pending_substitution_index),
        )

    if session.state == SessionState.AWAITING_DELIVERY_MODE:
        text = "\n\n".join(
            [
                labels.FINAL_RECIPE_READY_MESSAGE.format(recipe_name=session.final_recipe.recipe_name),
                labels.DELIVERY_MODE_PROMPT,
            ]
        )
        return text, delivery_handler.build_delivery_mode_keyboard()

    if session.state == SessionState.DELIVERING_INTERACTIVE:
        return (
            interactive_handler.build_step_message(session),
            interactive_handler.build_step_keyboard(session),
        )

    return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    bind_chat_context(chat_id)
    user = update.effective_user
    logger.info("start_command", chat_id=chat_id)

    session_factory = context.bot_data["session_factory"]
    async with session_scope(session_factory) as db_session:
        await UserRepository(db_session).get_or_create(user.id, user.username)

        session_service = SessionService(SessionRepository(db_session))
        session = await session_service.load_or_create(chat_id)

        if session.state in TRANSIENT_STATES:
            session = await session_service.reset(chat_id)

        if session.state not in QUERY_ACCEPTING_STATES:
            resume_content = _build_resume_content(session)
            if resume_content is not None:
                text, keyboard = resume_content
                await update.message.reply_text(labels.RESUME_PROMPT)
                await update.message.reply_text(text, reply_markup=keyboard)
                return

    await update.message.reply_text(labels.WELCOME_MESSAGE)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(labels.HELP_MESSAGE)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    bind_chat_context(chat_id)
    logger.info("cancel_command", chat_id=chat_id)

    session_factory = context.bot_data["session_factory"]
    async with session_scope(session_factory) as db_session:
        await SessionService(SessionRepository(db_session)).reset(chat_id)

    await update.message.reply_text(labels.CANCEL_MESSAGE)


async def handle_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Entry point for the ❌ cancel button shown on every in-flow keyboard.

    Same effect as the /cancel command, just reachable from a button tap at any point in the
    flow instead of typing a command.
    """
    query = update.callback_query
    await query.answer()

    chat_id = update.effective_chat.id
    bind_chat_context(chat_id)
    logger.info("cancel_button_pressed", chat_id=chat_id)

    session_factory = context.bot_data["session_factory"]
    async with session_scope(session_factory) as db_session:
        await SessionService(SessionRepository(db_session)).reset(chat_id)

    await query.edit_message_text(labels.CANCEL_MESSAGE)
