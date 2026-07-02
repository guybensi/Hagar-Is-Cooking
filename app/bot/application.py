from telegram.ext import Application

from app.bot.error_handler import handle_error
from app.config.settings import Settings, get_settings
from app.database.engine import create_engine, create_session_factory
from app.handlers.registry import register_handlers
from app.services.llm.groq_client import GroqClient
from app.services.recipe_extraction_service import RecipeExtractionService
from app.services.recipe_search_service import RecipeSearchService
from app.services.recipe_structuring_service import RecipeStructuringService
from app.services.substitution_service import SubstitutionService


def build_application(settings: Settings | None = None) -> Application:
    """Construct the PTB Application: shared services, handlers, and the error boundary.

    Performs no network I/O, so it's safe to call for smoke-testing configuration. Callers
    are responsible for running `init_db(application.bot_data["engine"])` before polling.
    """
    settings = settings or get_settings()

    application = Application.builder().token(settings.telegram_bot_token).build()

    engine = create_engine(settings.database_url)
    application.bot_data["engine"] = engine
    application.bot_data["session_factory"] = create_session_factory(engine)

    groq_client = GroqClient(api_key=settings.groq_api_key, model=settings.groq_model)
    application.bot_data["groq_client"] = groq_client
    application.bot_data["recipe_search_service"] = RecipeSearchService(
        api_key=settings.tavily_api_key
    )
    application.bot_data["recipe_extraction_service"] = RecipeExtractionService()
    application.bot_data["recipe_structuring_service"] = RecipeStructuringService(groq_client)
    application.bot_data["substitution_service"] = SubstitutionService(groq_client)

    register_handlers(application)
    application.add_error_handler(handle_error)

    return application
