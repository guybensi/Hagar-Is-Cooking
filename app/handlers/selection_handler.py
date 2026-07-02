from telegram import Update
from telegram.ext import ContextTypes

from app.database.engine import session_scope
from app.database.session_repository import SessionRepository
from app.models.session import ChecklistItem, SessionState
from app.services.recipe_extraction_service import RecipeExtractionError
from app.services.recipe_structuring_service import RecipeStructuringError
from app.services.session_service import SessionService
from app.static import labels
from app.static.emojis import CHECKED, PLATE
from app.utils.logging import get_logger
from app.utils.telegram_helpers import typing_action

logger = get_logger(__name__)


def _build_checklist_stub_message(structured_recipe) -> str:
    lines = [f"{PLATE} {structured_recipe.recipe_name}", "", labels.CHECKLIST_STUB_INTRO, ""]
    for ingredient in structured_recipe.ingredients:
        amount_suffix = f" - {ingredient.amount}" if ingredient.amount else ""
        lines.append(f"{CHECKED} {ingredient.name}{amount_suffix}")
    return "\n".join(lines)


async def handle_recipe_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Entry point for step 4-5: extract the selected recipe page and structure it via Groq."""
    query = update.callback_query
    await query.answer()

    chat_id = update.effective_chat.id
    selected_index = int(query.data.split(":", 1)[1])

    session_factory = context.bot_data["session_factory"]

    async with session_scope(session_factory) as db_session:
        session_service = SessionService(SessionRepository(db_session))
        session = await session_service.load_or_create(chat_id)

        if session.state != SessionState.AWAITING_RECIPE_SELECTION or selected_index >= len(
            session.search_results
        ):
            await query.edit_message_text(labels.STALE_SELECTION_MESSAGE)
            return

        selected_result = session.search_results[selected_index]

        await query.edit_message_text(labels.LOADING_RECIPE_MESSAGE)

        async with typing_action(context, chat_id):
            extraction_service = context.bot_data["recipe_extraction_service"]
            try:
                extracted = await extraction_service.extract_recipe(str(selected_result.url))
            except RecipeExtractionError:
                logger.error("recipe_extraction_failed", chat_id=chat_id, exc_info=True)
                await query.edit_message_text(labels.EXTRACTION_FAILED_MESSAGE)
                await session_service.advance_to(session, SessionState.AWAITING_DISH_QUERY)
                return

            structuring_service = context.bot_data["recipe_structuring_service"]
            try:
                structured = await structuring_service.structure(extracted)
            except RecipeStructuringError:
                logger.error("recipe_structuring_failed", chat_id=chat_id, exc_info=True)
                await query.edit_message_text(labels.STRUCTURING_FAILED_MESSAGE)
                await session_service.advance_to(session, SessionState.AWAITING_DISH_QUERY)
                return

        await query.edit_message_text(_build_checklist_stub_message(structured))

        await session_service.advance_to(
            session,
            SessionState.AWAITING_CHECKLIST,
            selected_index=selected_index,
            extracted_recipe=extracted,
            structured_recipe=structured,
            checklist=[
                ChecklistItem(name=i.name, amount=i.amount, checked=True)
                for i in structured.ingredients
            ],
        )
