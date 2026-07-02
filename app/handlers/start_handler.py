from telegram import Update
from telegram.ext import ContextTypes

from app.utils.logging import get_logger

logger = get_logger(__name__)

WELCOME_MESSAGE = (
    "שלום! 👋🍳\n"
    "אני העוזר האישי שלך למתכונים.\n"
    "פשוט ספר/י לי מה בא לך לבשל (למשל \"פסטה\" או \"משהו עם עוף\") ואני אמצא לך מתכון ממאקו.\n\n"
    "בכל שלב אפשר לשלוח /cancel כדי להתחיל מחדש."
)

HELP_MESSAGE = (
    "איך זה עובד? 🧑‍🍳\n"
    "1. ספר/י לי איזה מנה בא לך.\n"
    "2. אני אמצא 3 מתכונים ממאקו ותבחר/י אחד.\n"
    "3. נסמן יחד אילו מצרכים יש לך.\n"
    "4. אני אציע תחליפים למה שחסר.\n"
    "5. תקבל/י מתכון מותאם אישית — כמסמך מלא או צעד-אחר-צעד.\n\n"
    "/cancel - ביטול והתחלה מחדש"
)

CANCEL_MESSAGE = "בוטל. אפשר להתחיל מחדש בכל רגע — פשוט ספר/י לי מה בא לך לבשל 🍽️"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id if update.effective_chat else None
    logger.info("start_command", chat_id=chat_id)
    await update.message.reply_text(WELCOME_MESSAGE)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_MESSAGE)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id if update.effective_chat else None
    logger.info("cancel_command", chat_id=chat_id)
    await update.message.reply_text(CANCEL_MESSAGE)
