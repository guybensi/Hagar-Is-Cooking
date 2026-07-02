from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import Chat, Message, Update, User

from app.config.settings import Settings
from app.database.engine import create_engine, create_session_factory, init_db


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        telegram_bot_token="test-telegram-token",
        groq_api_key="test-groq-key",
        tavily_api_key="test-tavily-key",
        database_path=":memory:",
    )


@pytest.fixture
async def db_engine():
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    yield engine
    await engine.dispose()


@pytest.fixture
def session_factory(db_engine):
    return create_session_factory(db_engine)


def make_update(text: str | None = None, chat_id: int = 123, user_id: int = 456) -> MagicMock:
    """Build a fake telegram.Update for handler tests -- no real Telegram I/O."""
    chat = MagicMock(spec=Chat)
    chat.id = chat_id

    user = MagicMock(spec=User)
    user.id = user_id
    user.username = "test_user"

    message = MagicMock(spec=Message)
    message.text = text
    message.reply_text = AsyncMock()
    message.edit_text = AsyncMock()

    update = MagicMock(spec=Update)
    update.effective_chat = chat
    update.effective_user = user
    update.message = message
    update.callback_query = None

    return update


def make_context() -> MagicMock:
    context = MagicMock()
    context.bot.send_message = AsyncMock()
    context.bot.send_chat_action = AsyncMock()
    context.bot.edit_message_text = AsyncMock()
    context.user_data = {}
    context.chat_data = {}
    return context
