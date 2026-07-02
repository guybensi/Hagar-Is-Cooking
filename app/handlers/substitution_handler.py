from telegram import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.database.engine import session_scope
from app.database.session_repository import SessionRepository
from app.handlers.delivery_handler import build_delivery_mode_keyboard
from app.models.recipe import Ingredient
from app.models.session import SessionData, SessionState
from app.models.substitution import SubstitutionAction, SubstitutionDecision
from app.services.final_recipe_service import FinalRecipeGenerationError
from app.services.session_service import SessionService
from app.static import labels
from app.utils.logging import bind_chat_context, get_logger
from app.utils.telegram_helpers import cancel_row, typing_action

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
            cancel_row(),
        ]
    )


async def generate_and_render_final_recipe(
    query: CallbackQuery,
    context: ContextTypes.DEFAULT_TYPE,
    session_service: SessionService,
    session: SessionData,
) -> None:
    """Entry point for step 9: generate the ingredient-adapted final recipe via Groq.

    Shared by checklist_handler (when nothing needs substituting) and substitution_handler
    (once every proposed substitution has been answered).
    """
    chat_id = session.chat_id
    available = [Ingredient(name=i.name, amount=i.amount) for i in session.checklist if i.checked]

    accepted_names = {
        answer.ingredient_name for answer in session.substitution_answers if answer.accepted
    }
    missing = [
        Ingredient(name=i.name, amount=i.amount)
        for i in session.checklist
        if not i.checked and i.name not in accepted_names
    ]
    accepted_substitutions = [
        d
        for d in session.substitution_decisions
        if d.action == SubstitutionAction.SUBSTITUTE and d.ingredient_name in accepted_names
    ]

    async with typing_action(context, chat_id):
        final_recipe_service = context.bot_data["final_recipe_service"]
        try:
            final_recipe = await final_recipe_service.generate(
                session.structured_recipe, available, missing, accepted_substitutions
            )
        except FinalRecipeGenerationError:
            logger.error("final_recipe_generation_failed", chat_id=chat_id, exc_info=True)
            await query.edit_message_text(labels.FINAL_RECIPE_FAILED_MESSAGE)
            await session_service.advance_to(session, SessionState.AWAITING_CHECKLIST)
            return

    ready_message = "\n\n".join(
        [
            labels.FINAL_RECIPE_READY_MESSAGE.format(recipe_name=final_recipe.recipe_name),
            labels.DELIVERY_MODE_PROMPT,
        ]
    )
    await query.edit_message_text(ready_message, reply_markup=build_delivery_mode_keyboard())
    await session_service.advance_to(
        session, SessionState.AWAITING_DELIVERY_MODE, final_recipe=final_recipe
    )


async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Entry point for step 8: collect the user's yes/no answer for one substitution."""
    query = update.callback_query
    await query.answer()

    chat_id = update.effective_chat.id
    bind_chat_context(chat_id)
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

        await generate_and_render_final_recipe(query, context, session_service, session)
