from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from app.models.recipe import ExtractedRecipe, Ingredient, StructuredRecipe
from app.services.llm.groq_client import LLMStructuringError
from app.services.recipe_structuring_service import (
    RecipeStructuringError,
    RecipeStructuringService,
)


@pytest.fixture
def extracted() -> ExtractedRecipe:
    return ExtractedRecipe(
        source_url="https://www.mako.co.il/food/a",
        title="שניצל",
        raw_text="...",
        fetched_at=datetime.utcnow(),
    )


async def test_structure_returns_structured_recipe_on_success(extracted):
    groq_client = AsyncMock()
    groq_client.structure_recipe.return_value = StructuredRecipe(
        recipe_name="שניצל", ingredients=[Ingredient(name="עוף")], instructions=["לטגן"]
    )
    service = RecipeStructuringService(groq_client)

    result = await service.structure(extracted)

    assert result.recipe_name == "שניצל"
    groq_client.structure_recipe.assert_awaited_once_with(extracted)


async def test_structure_wraps_llm_structuring_error(extracted):
    groq_client = AsyncMock()
    groq_client.structure_recipe.side_effect = LLMStructuringError("boom")
    service = RecipeStructuringService(groq_client)

    with pytest.raises(RecipeStructuringError):
        await service.structure(extracted)
