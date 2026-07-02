from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from app.handlers import search_handler, selection_handler, start_handler


def register_handlers(application: Application) -> None:
    """Wire every command/message/callback handler onto the Application in one place."""
    application.add_handler(CommandHandler("start", start_handler.start))
    application.add_handler(CommandHandler("help", start_handler.help_command))
    application.add_handler(CommandHandler("cancel", start_handler.cancel))

    application.add_handler(
        CallbackQueryHandler(selection_handler.handle_recipe_selection, pattern=r"^select:\d+$")
    )

    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, search_handler.handle_free_text)
    )
