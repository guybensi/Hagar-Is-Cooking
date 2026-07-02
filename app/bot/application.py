from telegram.ext import Application

from app.bot.error_handler import handle_error
from app.config.settings import Settings, get_settings
from app.handlers.registry import register_handlers


def build_application(settings: Settings | None = None) -> Application:
    """Construct the PTB Application: register handlers and the global error boundary.

    Performs no network I/O, so it's safe to call for smoke-testing configuration.
    """
    settings = settings or get_settings()

    application = Application.builder().token(settings.telegram_bot_token).build()

    register_handlers(application)
    application.add_error_handler(handle_error)

    return application
