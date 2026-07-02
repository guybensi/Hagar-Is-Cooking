from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.database.engine import session_scope
from app.database.session_repository import SessionRepository
from app.models.session import SessionState
from app.models.substitution import SubstitutionAction, SubstitutionDecision
from app.services.session_service import SessionService
from app.static import labels
from app.utils.logging import get_logger

logger = get_logger(__name__)


def substitute_decisions(decisions: list[SubstitutionDecision]) -> list[SubstitutionDecision]:
    return [d for d in decisions if d.action == SubstitutionAction.SUBSTITUTE]


def build_substitution_question_message(decision: SubstitutionDecision) -> str:
    return labels.SUBSTITUTION_QUESTION.format(
        ingredient=decision.ingredient_name, replacement=decision.replacement
    )


def build_substitution_keyboard(index: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    labels.SUBSTITUTION_YES_BUTTON, callback_data=f"sub:{index}:yes"
                )
            ],
            [
                InlineKeyboardButton(
                    labels.SUBSTITUTION_NO_BUTTON, callback_data=f"sub:{index}:no"
                )
            ],
        ]
    )


async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Entry point for step 8: collect the user's yes/no answer for one substitution."""
    query = update.callback_query
    await query.answer()

    chat_id = update.effective_chat.id
    _, index_str, answer_str = query.data.split(":")
    index = int(index_str)
    accepted = answer_str == "yes"

    session_factory = context.bot_data["session_factory"]

    async with session_scope(session_factory) as db_session:
        session_service = SessionService(SessionRepository(db_session))
        session = await session_service.load_or_create(chat_id)

        pending = substitute_decisions(session.substitution_decisions)

        if (
            session.state != SessionState.AWAITING_SUBSTITUTION_ANSWERS
            or index != session.pending_substitution_index
            or index >= len(pending)
        ):
            await query.edit_message_text(labels.STALE_SELECTION_MESSAGE)
            return

        session.substitution_answers[index].accepted = accepted
        next_index = index + 1

        if next_index < len(pending):
            next_decision = pending[next_index]
            await query.edit_message_text(
                build_substitution_question_message(next_decision),
                reply_markup=build_substitution_keyboard(next_index),
            )
            await session_service.advance_to(
                session,
                SessionState.AWAITING_SUBSTITUTION_ANSWERS,
                substitution_answers=session.substitution_answers,
                pending_substitution_index=next_index,
            )
            return

        await query.edit_message_text(labels.GENERATING_FINAL_MESSAGE)
        await session_service.advance_to(
            session,
            SessionState.GENERATING_FINAL_RECIPE,
            substitution_answers=session.substitution_answers,
            pending_substitution_index=next_index,
        )
