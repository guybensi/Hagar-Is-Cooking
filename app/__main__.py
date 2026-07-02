import asyncio

from app.bot.application import build_application
from app.config.settings import get_settings
from app.database.engine import init_db
from app.utils.logging import configure_logging, get_logger

logger = get_logger(__name__)


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)

    application = build_application(settings)
    asyncio.run(init_db(application.bot_data["engine"]))

    logger.info("bot_starting")
    application.run_polling()


if __name__ == "__main__":
    main()
