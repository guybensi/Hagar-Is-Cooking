from telegram import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.database.engine import session_scope
from app.database.recipe_history_repository import RecipeHistoryRepository
from app.database.session_repository import SessionRepository
from app.models.session import SessionData, SessionState
from app.services.explanation_service import ExplanationError
from app.services.recipe_history_service import RecipeHistoryService
from app.services.session_service import SessionService
from app.static import labels
from app.utils.logging import bind_chat_context, get_logger
from app.utils.telegram_helpers import cancel_row
from app.utils.text import truncate

logger = get_logger(__name__)

_MAX_ALERT_LENGTH = 200


def build_step_message(session: SessionData) -> str:
    instructions = session.final_recipe.instructions
    header = labels.STEP_HEADER.format(
        step_number=session.current_step_index + 1, total_steps=len(instructions)
    )
    return f"{header}\n\n{instructions[session.current_step_index]}"


def build_step_keyboard(session: SessionData) -> InlineKeyboardMarkup:
    instructions = session.final_recipe.instructions
    is_first_step = session.current_step_index == 0
    is_last_step = session.current_step_index == len(instructions) - 1

    row = []
    if not is_first_step:
        row.append(InlineKeyboardButton(labels.PREVIOUS_STEP_BUTTON, callback_data="step:prev"))
    row.append(
        InlineKeyboardButton(
            labels.FINISH_COOKING_BUTTON if is_last_step else labels.DONE_STEP_BUTTON,
            callback_data="step:done",
        )
    )
    row.append(InlineKeyboardButton(labels.WHY_BUTTON, callback_data="step:why"))
    return InlineKeyboardMarkup(
        [
            row,
            [InlineKeyboardButton(labels.FULL_RECIPE_MODE_BUTTON, callback_data="mode:full")],
            cancel_row(),
        ]
    )


async def render_step(
    query: CallbackQuery, session_service: SessionService, session: SessionData
) -> None:
    await query.edit_message_text(
        build_step_message(session), reply_markup=build_step_keyboard(session)
    )
    await session_service.advance_to(
        session, SessionState.DELIVERING_INTERACTIVE, current_step_index=session.current_step_index
    )


async def handle_step_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Entry point for step 10b: navigate the interactive step-by-step recipe."""
    query = update.callback_query
    await query.answer()

    chat_id = update.effective_chat.id
    bind_chat_context(chat_id)
    action = query.data.split(":", 1)[1]

    session_factory = context.bot_data["session_factory"]
    async with session_scope(session_factory) as db_session:
        session_service = SessionService(SessionRepository(db_session))
        session = await session_service.load_or_create(chat_id)

        if session.state != SessionState.DELIVERING_INTERACTIVE or session.final_recipe is None:
            await query.edit_message_text(labels.STALE_SELECTION_MESSAGE)
            return

        total_steps = len(session.final_recipe.instructions)

        if action == "prev":
            session.current_step_index = max(0, session.current_step_index - 1)
            await render_step(query, session_service, session)
            return

        if session.current_step_index >= total_steps - 1:
            await query.edit_message_text(
                labels.COOKING_COMPLETE_MESSAGE.format(recipe_name=session.final_recipe.recipe_name)
            )
            history_service = RecipeHistoryService(RecipeHistoryRepository(db_session))
            await history_service.log_completed_once(
                session, update.effective_user.id, "interactive"
            )
            await session_service.advance_to(
                session, SessionState.COMPLETED, history_logged=session.history_logged
            )
            return

        session.current_step_index += 1
        await render_step(query, session_service, session)


async def handle_why(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Entry point for the 💡 button: explain why the current step matters.

    Answers the callback with a Telegram alert popup rather than editing the message, so the
    user is returned to exactly the same step afterwards with no extra round trip needed.
    """
    query = update.callback_query
    chat_id = update.effective_chat.id
    bind_chat_context(chat_id)

    session_factory = context.bot_data["session_factory"]
    async with session_scope(session_factory) as db_session:
        session_service = SessionService(SessionRepository(db_session))
        session = await session_service.load_or_create(chat_id)

        if session.state != SessionState.DELIVERING_INTERACTIVE or session.final_recipe is None:
            await query.answer(labels.STALE_SELECTION_MESSAGE, show_alert=True)
            return

        explanation_service = context.bot_data["explanation_service"]
        try:
            explanation = await explanation_service.explain(
                session.final_recipe, session.current_step_index
            )
        except ExplanationError:
            logger.error("step_explanation_failed", chat_id=chat_id, exc_info=True)
            await query.answer(labels.EXPLANATION_FAILED_MESSAGE, show_alert=True)
            return

        await query.answer(truncate(explanation, _MAX_ALERT_LENGTH), show_alert=True)
