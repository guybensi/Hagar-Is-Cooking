from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.database.engine import session_scope
from app.database.session_repository import SessionRepository
from app.models.session import ChecklistItem, SessionData, SessionState
from app.services.session_service import SessionService
from app.static import labels
from app.static.emojis import CHECKED, PLATE, UNCHECKED
from app.utils.logging import get_logger
from app.utils.text import truncate

logger = get_logger(__name__)


def build_checklist_message(recipe_name: str) -> str:
    return "\n".join([f"{PLATE} {recipe_name}", "", labels.CHECKLIST_INTRO])


def build_checklist_keyboard(checklist: list[ChecklistItem]) -> InlineKeyboardMarkup:
    rows = []
    for idx, item in enumerate(checklist):
        icon = CHECKED if item.checked else UNCHECKED
        label = f"{icon} {item.name}" + (f" - {item.amount}" if item.amount else "")
        rows.append([InlineKeyboardButton(truncate(label, 60), callback_data=f"toggle:{idx}")])
    rows.append([InlineKeyboardButton(labels.FINISHED_BUTTON, callback_data="finished")])
    return InlineKeyboardMarkup(rows)


async def handle_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    chat_id = update.effective_chat.id
    idx = int(query.data.split(":", 1)[1])

    session_factory = context.bot_data["session_factory"]
    async with session_scope(session_factory) as db_session:
        session_service = SessionService(SessionRepository(db_session))
        session = await session_service.load_or_create(chat_id)

        if session.state != SessionState.AWAITING_CHECKLIST or idx >= len(session.checklist):
            await query.edit_message_text(labels.STALE_SELECTION_MESSAGE)
            return

        session.checklist[idx].checked = not session.checklist[idx].checked

        await query.edit_message_text(
            build_checklist_message(session.structured_recipe.recipe_name),
            reply_markup=build_checklist_keyboard(session.checklist),
        )

        await session_service.advance_to(
            session, SessionState.AWAITING_CHECKLIST, checklist=session.checklist
        )


async def handle_finished(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    chat_id = update.effective_chat.id
    session_factory = context.bot_data["session_factory"]

    async with session_scope(session_factory) as db_session:
        session_service = SessionService(SessionRepository(db_session))
        session: SessionData = await session_service.load_or_create(chat_id)

        if session.state != SessionState.AWAITING_CHECKLIST:
            await query.edit_message_text(labels.STALE_SELECTION_MESSAGE)
            return

        await query.edit_message_text(labels.PROCESSING_CHECKLIST_MESSAGE)
        await session_service.advance_to(session, SessionState.DECIDING_SUBSTITUTIONS)
