from app.config.settings import Settings


def test_settings_reads_required_fields_from_kwargs():
    settings = Settings(
        telegram_bot_token="tg-token",
        groq_api_key="groq-key",
        tavily_api_key="tavily-key",
    )

    assert settings.telegram_bot_token == "tg-token"
    assert settings.groq_api_key == "groq-key"
    assert settings.tavily_api_key == "tavily-key"


def test_settings_defaults():
    settings = Settings(
        telegram_bot_token="tg-token",
        groq_api_key="groq-key",
        tavily_api_key="tavily-key",
    )

    assert settings.groq_model == "openai/gpt-oss-120b"
    assert settings.log_level == "INFO"


def test_database_url_built_from_database_path():
    settings = Settings(
        telegram_bot_token="tg-token",
        groq_api_key="groq-key",
        tavily_api_key="tavily-key",
        database_path="my.db",
    )

    assert settings.database_url == "sqlite+aiosqlite:///my.db"
