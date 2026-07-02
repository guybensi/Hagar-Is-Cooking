from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel

from app.services.llm.groq_client import GroqClient, LLMStructuringError


class _Answer(BaseModel):
    value: str


def _fake_completion(content: str) -> MagicMock:
    completion = MagicMock()
    completion.choices = [MagicMock(message=MagicMock(content=content))]
    return completion


@pytest.fixture
def groq_client() -> GroqClient:
    client = GroqClient(api_key="test-key", model="test-model")
    client._client = MagicMock()
    client._client.chat.completions.create = AsyncMock()
    return client


async def test_structured_completion_returns_valid_response(groq_client):
    groq_client._client.chat.completions.create.return_value = _fake_completion(
        '{"value": "hello"}'
    )

    result = await groq_client._structured_completion(
        system_prompt="sys", user_prompt="usr", response_model=_Answer
    )

    assert result == _Answer(value="hello")
    groq_client._client.chat.completions.create.assert_awaited_once()


async def test_structured_completion_retries_once_on_invalid_json_then_succeeds(groq_client):
    groq_client._client.chat.completions.create.side_effect = [
        _fake_completion("not json"),
        _fake_completion('{"value": "recovered"}'),
    ]

    result = await groq_client._structured_completion(
        system_prompt="sys", user_prompt="usr", response_model=_Answer
    )

    assert result == _Answer(value="recovered")
    assert groq_client._client.chat.completions.create.await_count == 2


async def test_structured_completion_raises_after_exhausting_retries(groq_client):
    groq_client._client.chat.completions.create.return_value = _fake_completion("still not json")

    with pytest.raises(LLMStructuringError):
        await groq_client._structured_completion(
            system_prompt="sys",
            user_prompt="usr",
            response_model=_Answer,
            max_validation_retries=1,
        )

    assert groq_client._client.chat.completions.create.await_count == 2


async def test_normalize_dish_query_returns_search_query_string(groq_client):
    groq_client._client.chat.completions.create.return_value = _fake_completion(
        '{"search_query": "פסטה ברוטב עגבניות"}'
    )

    result = await groq_client.normalize_dish_query("בא לי משהו עם פסטה ועגבניות")

    assert result == "פסטה ברוטב עגבניות"
