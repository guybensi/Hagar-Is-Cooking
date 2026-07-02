import asyncio

from app.bot.application import build_application
from app.config.settings import get_settings
from app.database.engine import create_engine, init_db
from app.utils.logging import configure_logging, get_logger

logger = get_logger(__name__)


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)

    engine = create_engine(settings.database_url)
    asyncio.run(init_db(engine))

    application = build_application(settings)
    logger.info("bot_starting")
    application.run_polling()


if __name__ == "__main__":
    main()
