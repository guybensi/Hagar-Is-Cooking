from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.database.engine import session_scope
from app.database.session_repository import SessionRepository
from app.handlers.substitution_handler import (
    build_substitution_keyboard,
    build_substitution_question_message,
    generate_and_render_final_recipe,
    substitute_decisions,
)
from app.models.recipe import Ingredient
from app.models.session import ChecklistItem, SessionData, SessionState
from app.models.substitution import SubstitutionAnswer
from app.services.session_service import SessionService
from app.services.substitution_service import SubstitutionDecisionError
from app.static import labels
from app.static.emojis import CHECKED, PLATE, UNCHECKED
from app.utils.logging import get_logger
from app.utils.telegram_helpers import typing_action
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
    """Entry point for step 7: decide BUY/SKIP/SUBSTITUTE for every missing ingredient."""
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

        missing = [item for item in session.checklist if not item.checked]

        if not missing:
            await query.edit_message_text(labels.GENERATING_FINAL_MESSAGE)
            await session_service.advance_to(
                session,
                SessionState.GENERATING_FINAL_RECIPE,
                substitution_decisions=[],
                substitution_answers=[],
            )
            await generate_and_render_final_recipe(query, context, session_service, session)
            return

        await query.edit_message_text(labels.PROCESSING_CHECKLIST_MESSAGE)

        async with typing_action(context, chat_id):
            substitution_service = context.bot_data["substitution_service"]
            missing_ingredients = [Ingredient(name=i.name, amount=i.amount) for i in missing]
            try:
                decisions = await substitution_service.decide(
                    missing_ingredients, session.structured_recipe
                )
            except SubstitutionDecisionError:
                logger.error("substitution_decision_failed", chat_id=chat_id, exc_info=True)
                await query.edit_message_text(labels.SUBSTITUTION_FAILED_MESSAGE)
                await session_service.advance_to(session, SessionState.AWAITING_CHECKLIST)
                return

        pending = substitute_decisions(decisions)

        if not pending:
            await query.edit_message_text(labels.GENERATING_FINAL_MESSAGE)
            await session_service.advance_to(
                session,
                SessionState.GENERATING_FINAL_RECIPE,
                substitution_decisions=decisions,
                substitution_answers=[],
            )
            await generate_and_render_final_recipe(query, context, session_service, session)
            return

        await query.edit_message_text(
            build_substitution_question_message(pending[0]),
            reply_markup=build_substitution_keyboard(0),
        )
        answers = [SubstitutionAnswer(ingredient_name=d.ingredient_name) for d in pending]
        await session_service.advance_to(
            session,
            SessionState.AWAITING_SUBSTITUTION_ANSWERS,
            substitution_decisions=decisions,
            substitution_answers=answers,
            pending_substitution_index=0,
        )
