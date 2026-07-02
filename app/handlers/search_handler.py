from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.database.engine import session_scope
from app.database.session_repository import SessionRepository
from app.models.search import SearchResult
from app.models.session import QUERY_ACCEPTING_STATES, SessionState
from app.services.session_service import SessionService
from app.static import labels
from app.static.emojis import PASTA
from app.utils.logging import get_logger
from app.utils.telegram_helpers import typing_action
from app.utils.text import truncate

logger = get_logger(__name__)


def _build_results_message(results: list[SearchResult]) -> str:
    lines = [labels.SEARCH_RESULTS_INTRO.format(count=len(results)), ""]
    lines += [f"{PASTA} {truncate(result.title)}" for result in results]
    lines += ["", labels.SEARCH_RESULTS_PROMPT]
    return "\n".join(lines)


def _build_results_keyboard(results: list[SearchResult]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    f"{PASTA} {truncate(result.title, 40)}", callback_data=f"select:{idx}"
                )
            ]
            for idx, result in enumerate(results)
        ]
    )


async def handle_free_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Entry point for step 1-3: understand the dish, search mako.co.il, show results."""
    chat_id = update.effective_chat.id
    user_text = (update.message.text or "").strip()

    session_factory = context.bot_data["session_factory"]

    async with session_scope(session_factory) as db_session:
        session_service = SessionService(SessionRepository(db_session))
        session = await session_service.load_or_create(chat_id)

        if session.state not in QUERY_ACCEPTING_STATES:
            await update.message.reply_text(labels.AWAITING_QUERY_NUDGE)
            return

        if not user_text:
            await update.message.reply_text(labels.EMPTY_QUERY_MESSAGE)
            return

        loading_message = await update.message.reply_text(labels.SEARCHING_MESSAGE)

        async with typing_action(context, chat_id):
            groq_client = context.bot_data["groq_client"]
            try:
                dish_query = await groq_client.normalize_dish_query(user_text)
            except Exception:
                logger.warning("normalize_dish_query_failed_falling_back", chat_id=chat_id)
                dish_query = user_text

            recipe_search_service = context.bot_data["recipe_search_service"]
            try:
                results = await recipe_search_service.search_recipes(dish_query)
            except Exception:
                logger.error("recipe_search_failed", chat_id=chat_id, exc_info=True)
                await loading_message.edit_text(labels.SEARCH_FAILED_MESSAGE)
                await session_service.reset(chat_id)
                return

        if not results:
            await loading_message.edit_text(labels.NO_RESULTS_MESSAGE)
            await session_service.advance_to(
                session, SessionState.AWAITING_DISH_QUERY, dish_query=dish_query, search_results=[]
            )
            return

        await loading_message.edit_text(
            _build_results_message(results),
            reply_markup=_build_results_keyboard(results),
        )

        await session_service.advance_to(
            session,
            SessionState.AWAITING_RECIPE_SELECTION,
            dish_query=dish_query,
            search_results=results,
            selected_index=None,
        )
