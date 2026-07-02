from telegram.ext import Application, CommandHandler

from app.handlers import start_handler


def register_handlers(application: Application) -> None:
    """Wire every command/message/callback handler onto the Application in one place."""
    application.add_handler(CommandHandler("start", start_handler.start))
    application.add_handler(CommandHandler("help", start_handler.help_command))
    application.add_handler(CommandHandler("cancel", start_handler.cancel))
