from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.database.engine import session_scope
from app.database.recipe_history_repository import RecipeHistoryRepository
from app.database.session_repository import SessionRepository
from app.handlers.interactive_handler import render_step
from app.models.recipe import FinalRecipe
from app.models.session import MODE_SWITCHABLE_STATES, SessionState
from app.services.recipe_history_service import RecipeHistoryService
from app.services.session_service import SessionService
from app.static import labels
from app.static.emojis import CHECKED, PLATE
from app.utils.logging import bind_chat_context, get_logger
from app.utils.telegram_helpers import cancel_row

logger = get_logger(__name__)


def build_delivery_mode_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    labels.INTERACTIVE_MODE_BUTTON, callback_data="mode:interactive"
                )
            ],
            [InlineKeyboardButton(labels.FULL_RECIPE_MODE_BUTTON, callback_data="mode:full")],
            cancel_row(),
        ]
    )


def build_full_recipe_keyboard() -> InlineKeyboardMarkup:
    """Lets the user switch to step-by-step mode after already viewing the full recipe."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    labels.INTERACTIVE_MODE_BUTTON, callback_data="mode:interactive"
                )
            ],
            cancel_row(),
        ]
    )


def build_full_recipe_message(recipe: FinalRecipe) -> str:
    lines = [f"{PLATE} {recipe.recipe_name}", "", labels.FULL_RECIPE_INGREDIENTS_HEADER]
    for ingredient in recipe.ingredients:
        amount_suffix = f" - {ingredient.amount}" if ingredient.amount else ""
        lines.append(f"{CHECKED} {ingredient.name}{amount_suffix}")

    lines += ["", labels.FULL_RECIPE_INSTRUCTIONS_HEADER]
    lines += [f"{idx + 1}. {step}" for idx, step in enumerate(recipe.instructions)]

    if recipe.cooking_tips:
        lines += ["", labels.FULL_RECIPE_TIPS_HEADER]
        lines += [f"- {tip}" for tip in recipe.cooking_tips]

    return "\n".join(lines)


async def handle_mode_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Entry point for step 10: deliver the final recipe as full text or interactive steps.

    Also handles switching between the two modes after the initial choice (mode:full /
    mode:interactive are reused as toggle buttons on the full-recipe message and on every
    interactive step).
    """
    query = update.callback_query
    await query.answer()

    chat_id = update.effective_chat.id
    bind_chat_context(chat_id)
    mode = query.data.split(":", 1)[1]

    session_factory = context.bot_data["session_factory"]
    async with session_scope(session_factory) as db_session:
        session_service = SessionService(SessionRepository(db_session))
        session = await session_service.load_or_create(chat_id)

        if session.state not in MODE_SWITCHABLE_STATES or session.final_recipe is None:
            await query.edit_message_text(labels.STALE_SELECTION_MESSAGE)
            return

        if mode == "full":
            await query.edit_message_text(
                build_full_recipe_message(session.final_recipe),
                reply_markup=build_full_recipe_keyboard(),
            )
            history_service = RecipeHistoryService(RecipeHistoryRepository(db_session))
            await history_service.log_completed_once(session, update.effective_user.id, "full")
            await session_service.advance_to(
                session,
                SessionState.COMPLETED,
                delivery_mode="full",
                history_logged=session.history_logged,
            )
            return

        # mode == "interactive": start fresh from step 1 the first time, resume where the user
        # left off if they're toggling back in from the full-recipe view.
        if session.state == SessionState.AWAITING_DELIVERY_MODE:
            session.current_step_index = 0

        await session_service.advance_to(
            session, SessionState.DELIVERING_INTERACTIVE, delivery_mode="interactive"
        )
        await render_step(query, session_service, session)
