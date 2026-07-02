from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.database.engine import session_scope
from app.database.session_repository import SessionRepository
from app.models.recipe import FinalRecipe
from app.models.session import SessionState
from app.services.session_service import SessionService
from app.static import labels
from app.static.emojis import CHECKED, PLATE
from app.utils.logging import get_logger

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
    """Entry point for step 10: deliver the final recipe as full text or interactive steps."""
    query = update.callback_query
    await query.answer()

    chat_id = update.effective_chat.id
    mode = query.data.split(":", 1)[1]

    session_factory = context.bot_data["session_factory"]
    async with session_scope(session_factory) as db_session:
        session_service = SessionService(SessionRepository(db_session))
        session = await session_service.load_or_create(chat_id)

        if session.state != SessionState.AWAITING_DELIVERY_MODE or session.final_recipe is None:
            await query.edit_message_text(labels.STALE_SELECTION_MESSAGE)
            return

        if mode == "full":
            await query.edit_message_text(build_full_recipe_message(session.final_recipe))
            await session_service.advance_to(
                session, SessionState.COMPLETED, delivery_mode="full"
            )
            return

        # mode == "interactive": full step-by-step navigation lands in the next increment.
        await query.edit_message_text(labels.INTERACTIVE_MODE_COMING_SOON_MESSAGE)
        await session_service.advance_to(
            session, SessionState.DELIVERING_INTERACTIVE, delivery_mode="interactive"
        )
