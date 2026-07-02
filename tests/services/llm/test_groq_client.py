from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel

from app.models.recipe import ExtractedRecipe, Ingredient, StructuredRecipe
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


async def test_structure_recipe_returns_structured_recipe(groq_client):
    groq_client._client.chat.completions.create.return_value = _fake_completion(
        '{"recipe_name": "שניצל", "ingredients": [{"name": "עוף", "amount": "500 גרם"}], '
        '"instructions": ["לטגן"]}'
    )
    extracted = ExtractedRecipe(
        source_url="https://www.mako.co.il/food/a",
        title="שניצל",
        raw_text="...",
        fetched_at=datetime.utcnow(),
    )

    result = await groq_client.structure_recipe(extracted)

    assert result.recipe_name == "שניצל"
    assert result.ingredients[0].name == "עוף"


async def test_decide_substitutions_returns_decision_list(groq_client):
    groq_client._client.chat.completions.create.return_value = _fake_completion(
        '{"decisions": [{"ingredient_name": "שורש סלרי", "action": "SUBSTITUTE", '
        '"reason": "דומה בטעם", "replacement": "שורש פטרוזיליה"}]}'
    )
    recipe = StructuredRecipe(
        recipe_name="שניצל",
        ingredients=[Ingredient(name="שורש סלרי")],
        instructions=["לטגן"],
    )

    result = await groq_client.decide_substitutions([Ingredient(name="שורש סלרי")], recipe)

    assert len(result) == 1
    assert result[0].replacement == "שורש פטרוזיליה"
